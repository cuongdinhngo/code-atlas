<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\Modifiers;
use PhpParser\Node;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitorAbstract;

/**
 * Turns one parsed file into contract nodes and bare edges.
 *
 * Runs after NameResolver, which resolves every reference to an FQN but writes it *without* a
 * leading backslash; the qualified-name convention requires one, so every name goes through
 * self::fqn(). Edges carry `target_raw` only — cross-file linking is the core resolver's job.
 */
final class Visitor extends NodeVisitorAbstract
{
    /** @var list<array<string, mixed>> */
    public array $nodes = [];

    /** @var list<array<string, mixed>> */
    public array $edges = [];

    private const CLASS_LIKE_KINDS = [
        Node\Stmt\Class_::class => 'Class',
        Node\Stmt\Interface_::class => 'Interface',
        Node\Stmt\Trait_::class => 'Trait',
        Node\Stmt\Enum_::class => 'Enum',
    ];

    private const IMPORT_TYPES = [
        Node\Stmt\Use_::TYPE_NORMAL => 'class',
        Node\Stmt\Use_::TYPE_FUNCTION => 'function',
        Node\Stmt\Use_::TYPE_CONSTANT => 'const',
    ];

    /**
     * Enclosing containers, innermost last, each as [opening node or null, qualified name].
     * The node is what leaveNode() matches on, so a declaration this visitor skipped — a
     * braced global namespace — never pops a scope it did not push.
     *
     * @var list<array{0: ?Node, 1: string}>
     */
    private array $scope;

    /**
     * Counts anonymous base qnames already emitted so a same-line collision gets a `:col` suffix (C1).
     *
     * @var array<string, int>
     */
    private array $anonymousOccurrences = [];

    /** @var list<array{fqn: string, alias: ?string, type: string}> */
    private array $imports = [];

    /**
     * Same-function string locals for `new $v` after `$v = 'FQN'` (task 030). Cleared per method/function.
     * Nested closures push/pop so an outer binding survives past a nested fn.
     *
     * @var array<string, string>
     */
    private array $stringLocals = [];

    /** @var list<array<string, string>> */
    private array $stringLocalsStack = [];

    public function __construct(
        private readonly string $path,
        int $lineCount,
        private readonly string $source = '',
        private readonly bool $declarationsOnly = false,
    ) {
        $this->scope = [[null, $path]];
        $this->nodes[] = [
            'kind' => 'File',
            'name' => basename($path),
            'qualified_name' => $path,
            'file_path' => $path,
            'line_start' => 1,
            'line_end' => $lineCount,
        ];
    }

    /**
     * @return int|null  ``DONT_TRAVERSE_CHILDREN`` to skip bodies when declarations-only
     */
    public function enterNode(Node $node)
    {
        // Nested closures/arrows carry no declarations we keep; skip before stack push/pop.
        if (
            $this->declarationsOnly
            && ($node instanceof Node\Expr\Closure || $node instanceof Node\Expr\ArrowFunction)
        ) {
            return NodeTraverser::DONT_TRAVERSE_CHILDREN;
        }

        if ($node instanceof Node\Stmt\Namespace_) {
            if ($node->name !== null) {
                $this->open($node, 'Namespace', $node->name->toString(), self::fqn($node->name));
            }
        } elseif ($node instanceof Node\Stmt\ClassLike) {
            if ($node->namespacedName !== null && $node->name !== null) {
                $this->enterClassLike($node, self::fqn($node->namespacedName), $node->name->toString());
            } elseif ($node instanceof Node\Stmt\Class_ && $node->name === null) {
                $this->enterAnonymousClass($node);
            }
        } elseif ($node instanceof Node\Stmt\Function_) {
            if ($node->namespacedName !== null) {
                $this->stringLocals = [];
                $this->open($node, 'Function', $node->name->toString(), self::fqn($node->namespacedName), [
                    'params' => $this->params($node->params),
                ] + $this->extraFields($this->attributeExtra($node->attrGroups)));
            }
            if ($this->declarationsOnly) {
                return NodeTraverser::DONT_TRAVERSE_CHILDREN;
            }
        } elseif ($node instanceof Node\Stmt\ClassMethod) {
            $this->stringLocals = [];
            if ($node->name->toString() === '__construct') {
                $this->declarePromotedProperties($node);
            }
            $this->open($node, 'Method', $node->name->toString(), $this->member($node->name->toString()), [
                'modifiers' => $this->methodModifiers($node),
                'params' => $this->params($node->params),
            ] + $this->extraFields($this->attributeExtra($node->attrGroups)));
            if ($this->declarationsOnly) {
                return NodeTraverser::DONT_TRAVERSE_CHILDREN;
            }
        } elseif ($node instanceof Node\Expr\Closure) {
            $this->stringLocalsStack[] = $this->stringLocals;
            $this->stringLocals = [];
            $this->enterClosureLike($node, 'closure', '{closure}', $node->params, $node->static, $node->attrGroups);
        } elseif ($node instanceof Node\Expr\ArrowFunction) {
            // fn() auto-captures by value — keep outer bindings; stack still restores on leave.
            $this->stringLocalsStack[] = $this->stringLocals;
            $this->enterClosureLike($node, 'fn', '{fn}', $node->params, $node->static, $node->attrGroups);
        } elseif ($node instanceof Node\Expr\Assign) {
            $this->enterAssign($node);
        } elseif ($node instanceof Node\Expr\AssignOp || $node instanceof Node\Expr\AssignRef) {
            $this->forgetStringLocal($node->var);
        } elseif ($node instanceof Node\Stmt\Foreach_) {
            $this->forgetStringLocal($node->valueVar);
            if ($node->keyVar !== null) {
                $this->forgetStringLocal($node->keyVar);
            }
        } elseif ($node instanceof Node\Stmt\Catch_ && $node->var !== null) {
            $this->forgetStringLocal($node->var);
        } elseif ($node instanceof Node\Stmt\Unset_) {
            foreach ($node->vars as $var) {
                $this->forgetStringLocal($var);
            }
        } else {
            $this->enterMemberOrReference($node);
        }

        return null;
    }

    public function leaveNode(Node $node)
    {
        if ($node instanceof Node\Expr\Closure || $node instanceof Node\Expr\ArrowFunction) {
            if ($this->stringLocalsStack !== []) {
                $this->stringLocals = array_pop($this->stringLocalsStack);
            }
        }
        if ($node instanceof Node\Stmt\Function_ || $node instanceof Node\Stmt\ClassMethod) {
            $this->stringLocals = [];
        }
        if ($this->scope[count($this->scope) - 1][0] === $node) {
            array_pop($this->scope);
        }

        return null;
    }

    /** Declarations that contain no members of their own, plus every reference edge. */
    private function enterMemberOrReference(Node $node): void
    {
        if (!$this->enterMemberDeclaration($node)) {
            $this->enterReference($node);
        }
    }

    /** Members that open no scope of their own. False means the node declared nothing. */
    private function enterMemberDeclaration(Node $node): bool
    {
        if ($node instanceof Node\Stmt\Property) {
            $this->enterProperty($node);
        } elseif ($node instanceof Node\Stmt\ClassConst) {
            $this->enterClassConst($node);
        } elseif ($node instanceof Node\Stmt\EnumCase) {
            $this->enterEnumCase($node);
        } elseif ($node instanceof Node\Stmt\Const_) {
            $this->enterGlobalConst($node);
        } else {
            return false;
        }

        return true;
    }

    /** Every edge pointing at something declared elsewhere; emits no node of its own. */
    private function enterReference(Node $node): void
    {
        if ($node instanceof Node\Stmt\TraitUse) {
            $this->enterTraitUse($node);
        } elseif ($node instanceof Node\Stmt\Use_) {
            $this->enterUse($node->type, $node->uses, null);
        } elseif ($node instanceof Node\Stmt\GroupUse) {
            $this->enterGroupUse($node);
        } elseif ($node instanceof Node\Expr\New_) {
            $this->enterNew($node);
        } elseif ($node instanceof Node\Expr\MethodCall || $node instanceof Node\Expr\NullsafeMethodCall) {
            if ($node->name instanceof Node\Identifier) {
                $this->enterInstanceCall($node, $node->name->toString());
            } else {
                // `$this->$method()` — genuinely dynamic method name (task 030 AC3).
                $this->edge(
                    'CALLS',
                    $this->container(),
                    '(dynamic)',
                    $node->getStartLine(),
                    'DYNAMIC',
                    $node,
                );
            }
        } elseif ($node instanceof Node\Expr\StaticCall
            && $node->class instanceof Node\Name
            && $node->name instanceof Node\Identifier
        ) {
            $this->enterStaticCall($node, $node->class, $node->name->toString());
        } elseif ($node instanceof Node\Expr\StaticCall
            && $node->class instanceof Node\Name
            && $node->name instanceof Node\Scalar\String_
        ) {
            // String method name is always HEURISTIC; still rewrite self/static/parent (Bugbot).
            $this->enterStaticCall($node, $node->class, $node->name->value, stringMethod: true);
        } elseif ($node instanceof Node\Expr\FuncCall && $node->name instanceof Node\Name) {
            $this->enterFuncCall($node, $node->name);
        } elseif ($node instanceof Node\Expr\Include_) {
            $this->enterInclude($node);
        }
    }

    /** $qname and $name are resolved by the caller, which is where their non-nullness is known. */
    private function enterClassLike(Node\Stmt\ClassLike $node, string $qname, string $name): void
    {
        $extra = $this->attributeExtra($node->attrGroups);
        if ($node instanceof Node\Stmt\Enum_ && $node->scalarType !== null) {
            $extra['scalar_type'] = self::typeName($node->scalarType);
        }
        $this->open($node, self::CLASS_LIKE_KINDS[$node::class], $name, $qname, [
            'modifiers' => $this->classModifiers($node),
        ] + $this->extraFields($extra));

        foreach ($this->parentsOf($node) as $parent) {
            $this->edge('EXTENDS', $qname, self::fqn($parent), $parent->getStartLine());
        }
        foreach ($this->interfacesOf($node) as $interface) {
            $this->edge('IMPLEMENTS', $qname, self::fqn($interface), $interface->getStartLine());
        }
    }

    private function enterAnonymousClass(Node\Stmt\Class_ $node): void
    {
        $qname = $this->anonymousQname($node, 'class');
        $this->open($node, 'Class', '{class}', $qname, [
            'modifiers' => $this->classModifiers($node),
        ] + $this->extraFields($this->attributeExtra($node->attrGroups)));

        foreach ($this->parentsOf($node) as $parent) {
            $this->edge('EXTENDS', $qname, self::fqn($parent), $parent->getStartLine());
        }
        foreach ($this->interfacesOf($node) as $interface) {
            $this->edge('IMPLEMENTS', $qname, self::fqn($interface), $interface->getStartLine());
        }
    }

    /**
     * @param Node\Param[]              $params
     * @param Node\AttributeGroup[]     $attrGroups
     */
    private function enterClosureLike(
        Node $node,
        string $anchor,
        string $name,
        array $params,
        bool $static,
        array $attrGroups,
    ): void {
        $fields = ['params' => $this->params($params)];
        if ($static) {
            $fields['modifiers'] = ['static'];
        }
        $fields += $this->extraFields($this->attributeExtra($attrGroups));
        $this->open($node, 'Function', $name, $this->anonymousQname($node, $anchor), $fields);
    }

    private function enterProperty(Node\Stmt\Property $node): void
    {
        $extra = [];
        if (($type = self::typeName($node->type)) !== null) {
            $extra['type'] = $type;
        }
        if ($node->hooks !== []) {
            $extra['hooks'] = array_map(
                static fn (Node\PropertyHook $hook): string => $hook->name->toString(),
                $node->hooks,
            );
        }
        $extra += $this->attributeExtra($node->attrGroups);
        foreach ($node->props as $property) {
            $name = '$' . $property->name->toString();
            $this->declare($property, 'Property', $name, $this->member($name), [
                'modifiers' => $this->propertyModifiers($node),
            ] + $this->extraFields($extra));
        }
    }

    private function enterClassConst(Node\Stmt\ClassConst $node): void
    {
        $extra = [];
        if (($type = self::typeName($node->type)) !== null) {
            $extra['type'] = $type;
        }
        $extra += $this->attributeExtra($node->attrGroups);
        foreach ($node->consts as $const) {
            $name = $const->name->toString();
            $this->declare($const, 'ClassConst', $name, $this->member($name), [
                'modifiers' => $this->classConstModifiers($node),
            ] + $this->extraFields($extra));
        }
    }

    private function enterEnumCase(Node\Stmt\EnumCase $node): void
    {
        $extra = ['enum_case' => true] + $this->attributeExtra($node->attrGroups);
        $name = $node->name->toString();
        $this->declare($node, 'ClassConst', $name, $this->member($name), $this->extraFields($extra));
    }

    private function enterGlobalConst(Node\Stmt\Const_ $node): void
    {
        foreach ($node->consts as $const) {
            $qname = $const->namespacedName !== null
                ? self::fqn($const->namespacedName)
                : self::fqn($const->name->toString());
            $this->declare($const, 'Const', $const->name->toString(), $qname);
        }
    }

    private function enterTraitUse(Node\Stmt\TraitUse $node): void
    {
        $owner = $this->container();
        foreach ($node->traits as $trait) {
            $this->edge('USES_TRAIT', $owner, self::fqn($trait), $trait->getStartLine());
        }

        $adaptations = [];
        foreach ($node->adaptations as $adaptation) {
            if ($adaptation instanceof Node\Stmt\TraitUseAdaptation\Alias) {
                $adaptations[] = [
                    'kind' => 'alias',
                    'trait' => $adaptation->trait !== null ? self::fqn($adaptation->trait) : null,
                    'method' => $adaptation->method->toString(),
                    'new_name' => $adaptation->newName?->toString(),
                ];
            } elseif ($adaptation instanceof Node\Stmt\TraitUseAdaptation\Precedence) {
                $adaptations[] = [
                    'kind' => 'insteadof',
                    'trait' => $adaptation->trait !== null ? self::fqn($adaptation->trait) : null,
                    'method' => $adaptation->method->toString(),
                    'insteadof' => array_map(self::fqn(...), $adaptation->insteadof),
                ];
            }
        }
        if ($adaptations !== []) {
            $this->appendExtraList($owner, 'trait_adaptations', $adaptations);
        }
    }

    /** @param Node\UseItem[] $uses */
    private function enterUse(int $type, array $uses, ?Node\Name $prefix): void
    {
        foreach ($uses as $use) {
            $fqn = self::fqn($prefix === null
                ? $use->name
                : $prefix->toString() . '\\' . $use->name->toString());
            $importType = self::IMPORT_TYPES[$use->type !== Node\Stmt\Use_::TYPE_UNKNOWN ? $use->type : $type]
                ?? 'class';
            $this->edge('IMPORTS', $this->path, $fqn, $use->getStartLine());
            $this->appendFileImport($fqn, $use->alias?->toString(), $importType);
        }
    }

    private function enterGroupUse(Node\Stmt\GroupUse $node): void
    {
        $this->enterUse($node->type, $node->uses, $node->prefix);
    }

    private function enterNew(Node\Expr\New_ $node): void
    {
        if ($node->class instanceof Node\Name) {
            $this->edge(
                'NEW', $this->container(), self::fqn($node->class), $node->getStartLine(), null, $node,
            );
        } elseif ($node->class instanceof Node\Stmt\Class_) {
            // Peek only — enterAnonymousClass registers the qname when the Class_ node is visited.
            $target = $this->anonymousQname($node->class, 'class', register: false);
            $this->edge('NEW', $this->container(), $target, $node->getStartLine(), null, $node);
        } elseif (
            $node->class instanceof Node\Expr\Variable
            && is_string($node->class->name)
            && isset($this->stringLocals[$node->class->name])
        ) {
            // `$v = 'FQN'; new $v` — same-function string local (task 030).
            $this->edge(
                'NEW',
                $this->container(),
                $this->stringLocals[$node->class->name],
                $node->getStartLine(),
                'HEURISTIC',
                $node,
            );
        } else {
            $this->edge(
                'NEW', $this->container(), '(dynamic)', $node->getStartLine(), 'DYNAMIC', $node,
            );
        }
    }

    /** Record `$v = 'string'` for same-function `new $v` HEURISTIC (task 030). */
    private function enterAssign(Node\Expr\Assign $node): void
    {
        if (
            $node->var instanceof Node\Expr\Variable
            && is_string($node->var->name)
            && $node->expr instanceof Node\Scalar\String_
        ) {
            $this->stringLocals[$node->var->name] = self::fqn($node->expr->value);
            return;
        }
        // Any other write we do not understand forgets the binding (AssignOp / list / …).
        $this->forgetStringLocal($node->var);
        if ($node->var instanceof Node\Expr\Array_ || $node->var instanceof Node\Expr\List_) {
            foreach ($node->var->items as $item) {
                if ($item !== null) {
                    $this->forgetStringLocal($item->value);
                }
            }
        }
    }

    /** Drop a tracked string local when the LHS is a plain variable we can name. */
    private function forgetStringLocal(Node $node): void
    {
        if ($node instanceof Node\Expr\Variable && is_string($node->name)) {
            unset($this->stringLocals[$node->name]);
        }
    }

    private function enterFuncCall(Node\Expr\FuncCall $node, Node\Name $name): void
    {
        if ($node->isFirstClassCallable()) {
            return;
        }
        $fn = strtolower(ltrim(self::fqn($name), '\\'));
        if ($fn === 'class_alias') {
            $this->enterClassAlias($node);
        } elseif ($fn === 'call_user_func') {
            $this->enterCallUserFunc($node);
        }
        $this->enterNamedCall($node, self::fqn($name));
    }

    private function enterClassAlias(Node\Expr\FuncCall $node): void
    {
        $args = $node->getArgs();
        if (count($args) < 2) {
            return;
        }
        $real = $args[0]->value;
        $alias = $args[1]->value;
        if (!($real instanceof Node\Scalar\String_) || !($alias instanceof Node\Scalar\String_)) {
            return;
        }
        // ALIASES from alias name → real class (ticket 030).
        $this->edge('ALIASES', self::fqn($alias->value), self::fqn($real->value), $node->getStartLine());
    }

    private function enterCallUserFunc(Node\Expr\FuncCall $node): void
    {
        $args = $node->getArgs();
        if ($args === []) {
            return;
        }
        $first = $args[0]->value;
        $target = null;
        if ($first instanceof Node\Scalar\String_) {
            $target = self::callableStringTarget($first->value);
        } elseif ($first instanceof Node\Expr\Array_ && count($first->items) >= 2) {
            $classItem = $first->items[0];
            $methodItem = $first->items[1];
            if (
                $classItem->value instanceof Node\Scalar\String_
                && $methodItem->value instanceof Node\Scalar\String_
            ) {
                $target = self::fqn($classItem->value->value) . '::' . $methodItem->value->value;
            }
        }
        if ($target !== null) {
            $this->edge('CALLS', $this->container(), $target, $node->getStartLine(), 'HEURISTIC');
        } else {
            $this->edge('CALLS', $this->container(), '(dynamic)', $node->getStartLine(), 'DYNAMIC');
        }
    }

    /** `'A::b'` / `'\\A\\b'` → FQN CALLS target; bare function name → FQN function. */
    private static function callableStringTarget(string $value): string
    {
        if (str_contains($value, '::')) {
            [$class, $method] = explode('::', $value, 2);

            return self::fqn($class) . '::' . $method;
        }

        return self::fqn($value);
    }

    private function enterInstanceCall(
        Node\Expr\MethodCall|Node\Expr\NullsafeMethodCall $node,
        string $method,
    ): void {
        if ($node->isFirstClassCallable()) {
            return;
        }
        // $this / $this?-> → enclosing FQN only when that class-like declares $method here.
        // Inherited / trait-mixin methods stay bare HEURISTIC so the name-match path still links.
        if ($node->var instanceof Node\Expr\Variable
            && $node->var->name === 'this'
            && ($owner = $this->enclosingDeclaringQname($method)) !== null
        ) {
            $this->edge(
                'CALLS', $this->container(), $owner . '::' . $method, $node->getStartLine(), null, $node,
            );
            return;
        }
        $this->edge(
            'CALLS', $this->container(), $method, $node->getStartLine(), 'HEURISTIC', $node,
        );
    }

    private function enterStaticCall(
        Node\Expr\StaticCall $node,
        Node\Name $class,
        string $method,
        bool $stringMethod = false,
    ): void {
        if ($node->isFirstClassCallable()) {
            return;
        }
        $special = strtolower($class->toString());
        if (($special === 'self' || $special === 'static')
            && ($owner = $this->enclosingDeclaringQname($method)) !== null
        ) {
            // static:: late binding, or string method name → HEURISTIC (C2 / task 030).
            $tier = ($special === 'static' || $stringMethod) ? 'HEURISTIC' : null;
            $this->edge(
                'CALLS', $this->container(), $owner . '::' . $method, $node->getStartLine(), $tier, $node,
            );
            return;
        }
        if ($special === 'parent' && ($parent = $this->enclosingParentQname()) !== null) {
            $tier = $stringMethod ? 'HEURISTIC' : null;
            $this->edge(
                'CALLS', $this->container(), $parent . '::' . $method, $node->getStartLine(), $tier, $node,
            );
            return;
        }
        if ($stringMethod) {
            $this->edge(
                'CALLS',
                $this->container(),
                self::fqn($class) . '::' . $method,
                $node->getStartLine(),
                'HEURISTIC',
                $node,
            );
            return;
        }
        $this->enterNamedCall($node, self::fqn($class) . '::' . $method);
    }

    private function enterNamedCall(Node\Expr\CallLike $node, string $target): void
    {
        if ($node->isFirstClassCallable()) {
            return;
        }
        $this->edge('CALLS', $this->container(), $target, $node->getStartLine(), null, $node);
    }

    /**
     * @param class-string<Node\Stmt\ClassLike> $type
     * @return array{0: Node, 1: string}|null
     */
    private function innermostScope(string $type): ?array
    {
        for ($i = count($this->scope) - 1; $i >= 0; $i--) {
            if ($this->scope[$i][0] instanceof $type) {
                return $this->scope[$i];
            }
        }

        return null;
    }

    /** Enclosing class-like qname only when it declares $method in this file (else name-match). */
    private function enclosingDeclaringQname(string $method): ?string
    {
        $frame = $this->innermostScope(Node\Stmt\ClassLike::class);
        if ($frame === null) {
            return null;
        }
        $node = $frame[0];
        assert($node instanceof Node\Stmt\ClassLike);

        return $node->getMethod($method) !== null ? $frame[1] : null;
    }

    /** FQN of the enclosing class's `extends` clause, when present in this file. */
    private function enclosingParentQname(): ?string
    {
        $frame = $this->innermostScope(Node\Stmt\Class_::class);
        if ($frame === null) {
            return null;
        }
        $node = $frame[0];
        assert($node instanceof Node\Stmt\Class_);
        // Innermost class only; no extends → leave \parent::… as today.
        return $node->extends !== null ? self::fqn($node->extends) : null;
    }

    private function declarePromotedProperties(Node\Stmt\ClassMethod $node): void
    {
        foreach ($node->params as $param) {
            if ($param->flags === 0) {
                continue;
            }
            $variable = $param->var;
            if (!$variable instanceof Node\Expr\Variable || !is_string($variable->name)) {
                continue;
            }
            $name = '$' . $variable->name;
            $extra = [];
            if (($type = self::typeName($param->type)) !== null) {
                $extra['type'] = $type;
            }
            $extra += $this->attributeExtra($param->attrGroups);
            $this->declare($param, 'Property', $name, $this->member($name), [
                'modifiers' => $this->promotedModifiers($param->flags),
            ] + $this->extraFields($extra));
        }
    }

    /** @return Node\Name[] — a class extends at most one parent, an interface may extend many. */
    private function parentsOf(Node\Stmt\ClassLike $node): array
    {
        if ($node instanceof Node\Stmt\Class_) {
            return $node->extends === null ? [] : [$node->extends];
        }

        return $node instanceof Node\Stmt\Interface_ ? $node->extends : [];
    }

    /** @return Node\Name[] */
    private function interfacesOf(Node\Stmt\ClassLike $node): array
    {
        return $node instanceof Node\Stmt\Class_ || $node instanceof Node\Stmt\Enum_
            ? $node->implements
            : [];
    }

    private function enterInclude(Node\Expr\Include_ $node): void
    {
        $literal = $node->expr instanceof Node\Scalar\String_ ? $node->expr->value : null;
        $this->edge(
            'INCLUDES',
            $this->container(),
            $literal ?? '(dynamic)',
            $node->getStartLine(),
            $literal === null ? 'DYNAMIC' : null
        );
    }

    /**
     * Record a declaration and make it the container for everything nested inside it.
     *
     * @param array<string, mixed> $fields
     */
    private function open(Node $node, string $kind, string $name, string $qname, array $fields = []): void
    {
        $this->declare($node, $kind, $name, $qname, $fields);
        $this->scope[] = [$node, $qname];
    }

    /** @param array<string, mixed> $fields */
    private function declare(Node $node, string $kind, string $name, string $qname, array $fields = []): void
    {
        $this->edge('CONTAINS', $this->container(), $qname, $node->getStartLine());
        $this->nodes[] = [
            'kind' => $kind,
            'name' => $name,
            'qualified_name' => $qname,
            'file_path' => $this->path,
            'line_start' => $node->getStartLine(),
            'line_end' => $node->getEndLine(),
        ] + $fields;
    }

    private function edge(
        string $kind,
        string $source,
        string $target,
        int $line,
        ?string $tier = null,
        ?Node\Expr\CallLike $call = null,
    ): void {
        // An omitted tier takes the store's RESOLVED default, so only a weaker claim is written.
        $edge = [
            'kind' => $kind,
            'source_qname' => $source,
            'target_raw' => $target,
            'file_path' => $this->path,
            'line' => $line,
        ];
        if ($tier !== null) {
            $edge['confidence_tier'] = $tier;
        }
        if ($call !== null && ($args = self::argLiterals($call)) !== null) {
            $edge['args'] = $args;
            $edge['arg_keys'] = self::argKeys($call);
        }
        $this->edges[] = $edge;
    }

    /**
     * One contract entry per argument: its literal *category*, or null when it is any other
     * expression. Values are never recorded — the question is "what shape", not "what value".
     *
     * @return list<string|null>|null
     */
    private static function argLiterals(Node\Expr\CallLike $call): ?array
    {
        if ($call->isFirstClassCallable()) {
            return null;
        }
        $out = [];
        foreach ($call->getArgs() as $arg) {
            // A spread forwards an unknown count and a named argument leaves its own position
            // open, so in both cases no position in this list can be trusted (PHP 8.0).
            if ($arg->unpack || $arg->name !== null) {
                return null;
            }
            $out[] = self::literalKind($arg->value);
        }

        return $out;
    }

    /**
     * Parallel to argLiterals: null for non-array args; ordered string keys for array literals.
     * Non-literal keys / unpack items contribute nothing and do not insert placeholders (063).
     *
     * @return list<list<string>|null>
     */
    private static function argKeys(Node\Expr\CallLike $call): array
    {
        $out = [];
        foreach ($call->getArgs() as $arg) {
            if ($arg->value instanceof Node\Expr\Array_) {
                $out[] = self::arrayLiteralStringKeys($arg->value);
            } else {
                $out[] = null;
            }
        }

        return $out;
    }

    /**
     * @return list<string>
     */
    private static function arrayLiteralStringKeys(Node\Expr\Array_ $array): array
    {
        $keys = [];
        foreach ($array->items as $item) {
            if ($item->unpack || $item->key === null) {
                continue;
            }
            if ($item->key instanceof Node\Scalar\String_) {
                $keys[] = $item->key->value;
            } elseif ($item->key instanceof Node\Scalar\InterpolatedString) {
                // Interpolated keys are not a fixed string — contribute nothing (063).
                continue;
            }
            // Non-literal keys ($k => …) contribute nothing and do not shift later keys.
        }

        return $keys;
    }

    private static function literalKind(Node\Expr $value): ?string
    {
        if ($value instanceof Node\Scalar\String_ || $value instanceof Node\Scalar\InterpolatedString) {
            return 'string';
        }
        if ($value instanceof Node\Scalar\Int_ || $value instanceof Node\Scalar\Float_) {
            return 'number';
        }
        if ($value instanceof Node\Expr\Array_) {
            return 'array';
        }
        if ($value instanceof Node\Expr\ConstFetch) {
            $name = strtolower($value->name->toString());

            return in_array($name, ['null', 'true', 'false'], true) ? $name : null;
        }

        return null;
    }

    private function container(): string
    {
        return $this->scope[count($this->scope) - 1][1];
    }

    private function member(string $name): string
    {
        return $this->container() . '::' . $name;
    }

    private function anonymousQname(Node $node, string $kind, bool $register = true): string
    {
        $base = $this->container() . '::{' . $kind . '@' . $node->getStartLine() . '}';
        $seen = $this->anonymousOccurrences[$base] ?? 0;
        if ($register) {
            $this->anonymousOccurrences[$base] = $seen + 1;
        }
        // First on the line keeps the H1 base form; later ones append :col (ticket C1).
        if ($seen === 0) {
            return $base;
        }

        return $base . ':' . $this->columnOf($node);
    }

    /** 1-based column of the node's start within its source line. */
    private function columnOf(Node $node): int
    {
        $pos = $node->getStartFilePos();
        if ($pos < 0 || $this->source === '') {
            return 1;
        }
        $newline = strrpos(substr($this->source, 0, $pos), "\n");

        return $newline === false ? $pos + 1 : $pos - $newline;
    }

    /**
     * @param Node\Param[] $params
     *
     * @return list<array{name: string, type: ?string}>
     */
    private function params(array $params): array
    {
        $signature = [];
        foreach ($params as $param) {
            $variable = $param->var;
            $signature[] = [
                'name' => $variable instanceof Node\Expr\Variable && is_string($variable->name)
                    ? '$' . $variable->name
                    : '$?',
                'type' => self::typeName($param->type),
            ];
        }

        return $signature;
    }

    /** @return list<string> */
    private function classModifiers(Node\Stmt\ClassLike $node): array
    {
        if (!$node instanceof Node\Stmt\Class_) {
            return [];
        }

        return $this->flags([
            'abstract' => $node->isAbstract(),
            'final' => $node->isFinal(),
            'readonly' => $node->isReadonly(),
        ]);
    }

    /** @return list<string> */
    private function methodModifiers(Node\Stmt\ClassMethod $node): array
    {
        return array_merge([$this->visibilityOf($node->isPrivate(), $node->isProtected())], $this->flags([
            'static' => $node->isStatic(),
            'abstract' => $node->isAbstract(),
            'final' => $node->isFinal(),
        ]));
    }

    /** @return list<string> */
    private function propertyModifiers(Node\Stmt\Property $node): array
    {
        return array_merge([$this->visibilityOf($node->isPrivate(), $node->isProtected())], $this->flags([
            'static' => $node->isStatic(),
            'readonly' => $node->isReadonly(),
        ]));
    }

    /** @return list<string> */
    private function classConstModifiers(Node\Stmt\ClassConst $node): array
    {
        return array_merge([$this->visibilityOf($node->isPrivate(), $node->isProtected())], $this->flags([
            'final' => $node->isFinal(),
        ]));
    }

    /** @return list<string> */
    private function promotedModifiers(int $flags): array
    {
        return array_merge([
            $this->visibilityOf(
                ($flags & Modifiers::PRIVATE) !== 0,
                ($flags & Modifiers::PROTECTED) !== 0,
            ),
        ], $this->flags([
            'readonly' => ($flags & Modifiers::READONLY) !== 0,
        ]));
    }

    private function visibilityOf(bool $private, bool $protected): string
    {
        return $private ? 'private' : ($protected ? 'protected' : 'public');
    }

    /**
     * @param array<string, bool> $flags
     *
     * @return list<string>
     */
    private function flags(array $flags): array
    {
        return array_keys(array_filter($flags));
    }

    /**
     * Attributes as an `extra` fragment. Never hand rawAttributes() to extraFields() directly:
     * a bare list lands the attributes *as* `extra` instead of under `extra.attributes`.
     *
     * @param Node\AttributeGroup[] $attrGroups
     *
     * @return array<string, mixed>
     */
    private function attributeExtra(array $attrGroups): array
    {
        $attributes = $this->rawAttributes($attrGroups);

        return $attributes === [] ? [] : ['attributes' => $attributes];
    }

    /**
     * @param Node\AttributeGroup[] $attrGroups
     *
     * @return list<array{name: string, args: list<mixed>}>
     */
    private function rawAttributes(array $attrGroups): array
    {
        $attributes = [];
        foreach ($attrGroups as $group) {
            foreach ($group->attrs as $attr) {
                $attributes[] = [
                    'name' => self::fqn($attr->name),
                    'args' => array_map($this->rawAttrArg(...), $attr->args),
                ];
            }
        }

        return $attributes;
    }

    private function rawAttrArg(Node\Arg $arg): mixed
    {
        $value = $arg->value;
        if ($value instanceof Node\Scalar\String_
            || $value instanceof Node\Scalar\Int_
            || $value instanceof Node\Scalar\Float_
        ) {
            return $value->value;
        }
        if ($value instanceof Node\Expr\ConstFetch) {
            return $value->name->toString();
        }

        return null;
    }

    /**
     * @param array<string, mixed> $extra
     *
     * @return array{extra?: array<string, mixed>}
     */
    private function extraFields(array $extra): array
    {
        return $extra === [] ? [] : ['extra' => $extra];
    }

    private function appendFileImport(string $fqn, ?string $alias, string $type): void
    {
        // Imports are the only `extra` the File node ever carries, so this rewrites rather than merges.
        $this->imports[] = ['fqn' => $fqn, 'alias' => $alias, 'type' => $type];
        $this->nodes[0]['extra'] = ['imports' => $this->imports];
    }

    /** @param list<array<string, mixed>> $items */
    private function appendExtraList(string $qname, string $key, array $items): void
    {
        foreach ($this->nodes as $index => $node) {
            if (($node['qualified_name'] ?? null) !== $qname) {
                continue;
            }
            $current = $node['extra'] ?? [];
            $extra = is_array($current) ? $current : [];
            $existing = $extra[$key] ?? [];
            $extra[$key] = array_merge(is_array($existing) ? $existing : [], $items);
            $this->nodes[$index]['extra'] = $extra;

            return;
        }
    }

    /** Every declared type, not just class names: a scalar hint dropped to null reads as untyped. */
    private static function typeName(?Node $type): ?string
    {
        if ($type instanceof Node\Name) {
            return self::fqn($type);
        }
        if ($type instanceof Node\Identifier) {
            return $type->toString();
        }
        if ($type instanceof Node\NullableType) {
            return '?' . self::typeName($type->type);
        }
        if ($type instanceof Node\UnionType || $type instanceof Node\IntersectionType) {
            $glue = $type instanceof Node\UnionType ? '|' : '&';

            return implode($glue, array_map(self::typeName(...), $type->types));
        }

        return null;
    }

    /** The convention anchors every qualified name at the global namespace. */
    private static function fqn(Node\Name|string $name): string
    {
        return '\\' . ltrim((string) $name, '\\');
    }
}
