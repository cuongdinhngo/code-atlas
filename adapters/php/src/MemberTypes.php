<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\NameContext;
use PhpParser\Node;
use PhpParser\NodeVisitorAbstract;

/**
 * What every class-like declared in THIS file holds: its members' declared types and what it
 * inherits from. Collected in a pass of its own because a method may call one declared below it.
 *
 * Deliberately file-local (R3.3): a single file cannot know all targets, so an unknown class here
 * means "ask the resolver", never "no such member". Anonymous classes are skipped — their
 * qualified name depends on traversal state that only the emitting visitor holds.
 */
final class MemberTypes extends NodeVisitorAbstract
{
    /**
     * @var array<string, array{
     *     parents: list<string>,
     *     extends: ?string,
     *     methods: array<string, ?string>,
     *     properties: array<string, ?string>,
     *     inherits: bool,
     * }>
     */
    private array $classes = [];

    /** @var array<string, ?string> */
    private array $functions = [];

    /** @var list<string> */
    private array $open = [];

    /** How far a member lookup may climb this file's own hierarchy before giving up. */
    private const MAX_DEPTH = 64;

    /** The resolver's live name context: `use` imports and the namespace in force (393). */
    private ?NameContext $names = null;

    /** @var array<string, string> `\Class::method` → the class its `@return` docblock names */
    private array $docReturns = [];

    /** @var array<string, string> `\Class::$p` → the class its `@var` docblock names (447) */
    private array $docVars = [];

    /** @var array<string, string|false> `\Class::$p` → what `$this->p = new X` assigns; false: any other write */
    private array $assigned = [];

    /** @var array<string, array<string, true>> `$p` → every class-like here that writes `$this->p` */
    private array $writers = [];

    /** Names a docblock type never resolves to a class: PHP's own types and pseudo-types. */
    private const NOT_A_CLASS = [
        'array', 'bool', 'callable', 'false', 'float', 'int', 'iterable', 'mixed', 'never',
        'null', 'object', 'parent', 'resource', 'self', 'static', 'string', 'true', 'void',
        'boolean', 'double', 'integer', 'number', 'numeric', 'scalar',
    ];

    public function useNameContext(NameContext $names): void
    {
        $this->names = $names;
    }

    public function enterNode(Node $node)
    {
        if ($node instanceof Node\Stmt\ClassLike) {
            $this->enterClassLike($node);
        } elseif ($node instanceof Node\Stmt\TraitUse) {
            $this->addParents(array_values(array_map(TypeName::of(...), $node->traits)));
        } elseif ($node instanceof Node\Stmt\ClassMethod) {
            $this->addMethod($node);
        } elseif ($node instanceof Node\Stmt\Property) {
            $this->addProperty($node);
        } elseif ($node instanceof Node\Stmt\Function_ && $node->namespacedName !== null) {
            $this->functions[Qname::of($node->namespacedName)] = TypeName::of($node->returnType);
        }

        return null;
    }

    public function leaveNode(Node $node)
    {
        // On leave: NameResolver has qualified the `new X` below by now.
        if ($node instanceof Node\Expr\Assign || $node instanceof Node\Expr\AssignOp
            || $node instanceof Node\Expr\AssignRef
        ) {
            $this->observeWrite($node);
        } elseif ($node instanceof Node\Stmt\Foreach_) {
            $this->observeTarget($node->keyVar, null);
            $this->observeTarget($node->valueVar, null);
        }
        if ($node instanceof Node\Stmt\ClassLike && $this->open !== []) {
            array_pop($this->open);
        }

        return null;
    }

    private function enterClassLike(Node\Stmt\ClassLike $node): void
    {
        if ($node->namespacedName === null) {
            // Anonymous: push a blank frame so leaveNode stays balanced, record nothing.
            $this->open[] = '';

            return;
        }
        $qname = Qname::of($node->namespacedName);
        $extends = null;
        $parents = [];
        if ($node instanceof Node\Stmt\Class_ && $node->extends !== null) {
            $extends = TypeName::of($node->extends);
            $parents[] = $extends;
        }
        if ($node instanceof Node\Stmt\Interface_) {
            $parents = array_map(TypeName::of(...), $node->extends);
        }
        if ($node instanceof Node\Stmt\Class_ || $node instanceof Node\Stmt\Enum_) {
            $parents = array_merge($parents, array_map(TypeName::of(...), $node->implements));
        }
        $parents = array_values(array_filter($parents, static fn (?string $p): bool => $p !== null));
        $this->classes[$qname] = [
            'parents' => $parents,
            'extends' => $extends,
            'methods' => [],
            'properties' => [],
            // A trait's `$this` is the using class, so a trait never inherits on its own behalf.
            'inherits' => $parents !== [] && !$node instanceof Node\Stmt\Trait_,
        ];
        $this->open[] = $qname;
    }

    /** @param list<?string> $parents */
    private function addParents(array $parents): void
    {
        $current = $this->current();
        if ($current === null) {
            return;
        }
        $entry = $this->classes[$current];
        foreach ($parents as $parent) {
            if ($parent !== null) {
                $entry['parents'][] = $parent;
                $entry['inherits'] = true;
            }
        }
        $this->classes[$current] = $entry;
    }

    private function addMethod(Node\Stmt\ClassMethod $node): void
    {
        $current = $this->current();
        if ($current === null) {
            return;
        }
        $entry = $this->classes[$current];
        $entry['methods'][$node->name->toString()] = TypeName::of($node->returnType);
        if ($node->returnType === null && ($doc = $this->docClass($node, 'return')) !== null) {
            $this->docReturns[Qname::member($current, $node->name->toString())] = $doc;
        }
        foreach ($node->params as $param) {
            // Constructor promotion declares a property from a parameter (PHP 8.0).
            if ($param->flags === 0 || !$param->var instanceof Node\Expr\Variable) {
                continue;
            }
            if (is_string($param->var->name)) {
                $entry['properties']['$' . $param->var->name] = TypeName::of($param->type);
                // Promotion assigns the argument: that is a write no `new X` can type (447).
                $this->assigned[Qname::member($current, '$' . $param->var->name)] = false;
            }
        }
        $this->classes[$current] = $entry;
    }

    private function addProperty(Node\Stmt\Property $node): void
    {
        $current = $this->current();
        if ($current === null) {
            return;
        }
        $entry = $this->classes[$current];
        foreach ($node->props as $property) {
            $name = '$' . $property->name->toString();
            $entry['properties'][$name] = TypeName::of($node->type);
            $qname = Qname::member($current, $name);
            if ($node->type === null && ($doc = $this->docClass($node, 'var')) !== null) {
                $this->docVars[$qname] = $doc;
            }
            // A default other than `null` is a value no `new X` assigned (447).
            if ($property->default !== null && !self::isNull($property->default)) {
                $this->assigned[$qname] = false;
            }
        }
        $this->classes[$current] = $entry;
    }

    private static function isNull(Node\Expr $expr): bool
    {
        return $expr instanceof Node\Expr\ConstFetch && strtolower($expr->name->toString()) === 'null';
    }

    /**
     * `$this->p = new X(...)` (or `??=`) records X against the writing class-like; any other write
     * to `$this->p` — another class, a value, a reference, a destructure, a `foreach` — records false.
     */
    private function observeWrite(Node\Expr\Assign|Node\Expr\AssignOp|Node\Expr\AssignRef $node): void
    {
        if ($node instanceof Node\Expr\Assign
            && ($node->var instanceof Node\Expr\List_ || $node->var instanceof Node\Expr\Array_)
        ) {
            $this->observeTarget($node->var, null);

            return;
        }
        $typed = $node instanceof Node\Expr\Assign || $node instanceof Node\Expr\AssignOp\Coalesce;
        $current = $this->current();
        $class = $typed && $current !== null ? $this->newClass($node->expr, $current) : null;
        $this->observeTarget($node->var, $class);
    }

    /** One write target: a `$this->p` records ``$class`` (null: untyped); a destructure recurses. */
    private function observeTarget(?Node\Expr $target, ?string $class): void
    {
        if ($target instanceof Node\Expr\List_ || $target instanceof Node\Expr\Array_) {
            foreach ($target->items as $item) {
                $this->observeTarget($item?->value, null);
            }

            return;
        }
        $current = $this->current();
        if ($current === null
            || !$target instanceof Node\Expr\PropertyFetch
            || !$target->var instanceof Node\Expr\Variable
            || $target->var->name !== 'this'
            || !$target->name instanceof Node\Identifier
        ) {
            return;
        }
        $name = '$' . $target->name->toString();
        $qname = Qname::member($current, $name);
        $this->writers[$name][$current] = true;
        $previous = $this->assigned[$qname] ?? null;
        $this->assigned[$qname] = $class !== null && ($previous === null || $previous === $class) ? $class : false;
    }

    /** The class a `new` names, `self` / `static` / `parent` read from where it was written. */
    private function newClass(Node\Expr $expr, string $current): ?string
    {
        if (!$expr instanceof Node\Expr\New_ || !$expr->class instanceof Node\Name) {
            return null;
        }
        $name = TypeName::of($expr->class);
        if ($name === TypeName::PARENT) {
            return $this->extendsOf($current);
        }

        return $name === TypeName::SELF || $name === TypeName::STATIC_ ? $current : $name;
    }

    /**
     * The class an untyped property holds: its `@var` docblock, else the one class the declaring
     * class's writes assign — unless a trait or class it is related to here writes otherwise (447).
     */
    public function propertyClass(string $property): ?string
    {
        if (isset($this->docVars[$property])) {
            return $this->docVars[$property];
        }
        $assigned = $this->assigned[$property] ?? null;
        if (!is_string($assigned)) {
            return null;
        }
        [$declarer, $name] = explode(Qname::MEMBER, $property, 2);
        foreach (array_keys($this->writers[$name] ?? []) as $writer) {
            $related = in_array($declarer, $this->ancestry($writer), true)
                || in_array($writer, $this->ancestry($declarer), true);
            if ($related && ($this->assigned[Qname::member($writer, $name)] ?? null) !== $assigned) {
                return null;
            }
        }

        return $assigned;
    }

    /** @return list<string> the class-likes ``$class`` inherits from or uses, as far as this file says */
    private function ancestry(string $class): array
    {
        $queue = [$class];
        for ($index = 0; $index < count($queue) && $index < self::MAX_DEPTH; $index++) {
            foreach ($this->classes[$queue[$index]]['parents'] ?? [] as $parent) {
                if (!in_array($parent, $queue, true)) {
                    $queue[] = $parent;
                }
            }
        }

        return $queue;
    }

    private function current(): ?string
    {
        $top = $this->open === [] ? '' : $this->open[count($this->open) - 1];

        return $top === '' ? null : $top;
    }

    public function knows(string $class): bool
    {
        return isset($this->classes[$class]);
    }

    /** True when this class can hold a member it does not declare here (extends/implements/uses). */
    public function inherits(string $class): bool
    {
        return $this->classes[$class]['inherits'] ?? false;
    }

    public function extendsOf(string $class): ?string
    {
        return $this->classes[$class]['extends'] ?? null;
    }

    /**
     * The declared return type of ``$class::$method``, with the class that declared it.
     *
     * @return array{type: ?string, declaredBy: string}|null  null when this file cannot say
     */
    public function method(string $class, string $method): ?array
    {
        return $this->lookup($class, 'methods', $method);
    }

    /**
     * @return array{type: ?string, declaredBy: string}|null
     */
    public function property(string $class, string $property): ?array
    {
        return $this->lookup($class, 'properties', $property);
    }

    /**
     * @param 'methods'|'properties' $bag
     *
     * @return array{type: ?string, declaredBy: string}|null
     */
    private function lookup(string $class, string $bag, string $member): ?array
    {
        $queue = [$class];
        $seen = [$class => true];
        for ($index = 0; $index < count($queue) && $index < self::MAX_DEPTH; $index++) {
            $current = $queue[$index];
            if (!isset($this->classes[$current])) {
                continue;
            }
            if (array_key_exists($member, $this->classes[$current][$bag])) {
                return ['type' => $this->classes[$current][$bag][$member], 'declaredBy' => $current];
            }
            foreach ($this->classes[$current]['parents'] as $parent) {
                if (!isset($seen[$parent])) {
                    $seen[$parent] = true;
                    $queue[] = $parent;
                }
            }
        }

        return null;
    }

    /**
     * The one class a `@return` (393) or `@var` (447) docblock names, resolved like code. A union
     * other than `X|null` / `null|X`, a generic, or a PHP type reads as nothing — a docblock is a claim.
     *
     * @param 'return'|'var' $tag
     */
    private function docClass(Node\Stmt\ClassMethod|Node\Stmt\Property $node, string $tag): ?string
    {
        $comment = $node->getDocComment();
        if ($comment === null || $this->names === null) {
            return null;
        }
        // The tag opens its docblock line; `@return` inside prose is not one.
        $pattern = '/^[\s\/*]*@' . $tag . '\s+(?:null\|)?\??(\\\\?[A-Za-z_][\w\\\\]*)(?:\|null)?(?=\s|\*|$)/m';
        if (preg_match($pattern, $comment->getText(), $match) !== 1) {
            return null;
        }
        $written = $match[1];
        $lower = strtolower($written);
        if (in_array($lower, self::NOT_A_CLASS, true) || str_starts_with($lower, 'namespace\\')) {
            return null;
        }
        if (str_starts_with($written, '\\')) {
            return Qname::of(new Node\Name\FullyQualified(substr($written, 1)));
        }

        return Qname::of($this->names->getResolvedClassName(new Node\Name($written)));
    }

    /** The class ``$method``'s `@return` docblock names, when it declares no return type. */
    public function docReturn(string $method): ?string
    {
        return $this->docReturns[$method] ?? null;
    }

    public function functionReturn(string $qname): ?string
    {
        return $this->functions[$qname] ?? null;
    }
}
