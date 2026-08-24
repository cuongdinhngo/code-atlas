<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

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
        foreach ($node->params as $param) {
            // Constructor promotion declares a property from a parameter (PHP 8.0).
            if ($param->flags === 0 || !$param->var instanceof Node\Expr\Variable) {
                continue;
            }
            if (is_string($param->var->name)) {
                $entry['properties']['$' . $param->var->name] = TypeName::of($param->type);
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
            $entry['properties']['$' . $property->name->toString()] = TypeName::of($node->type);
        }
        $this->classes[$current] = $entry;
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

    public function functionReturn(string $qname): ?string
    {
        return $this->functions[$qname] ?? null;
    }
}
