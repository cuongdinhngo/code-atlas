<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\Node;
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

    /**
     * Enclosing containers, innermost last, each as [opening node or null, qualified name].
     * The node is what leaveNode() matches on, so a declaration this visitor skipped — an
     * anonymous class, a braced global namespace — never pops a scope it did not push.
     *
     * @var list<array{0: ?Node, 1: string}>
     */
    private array $scope;

    public function __construct(private readonly string $path, int $lineCount)
    {
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

    public function enterNode(Node $node)
    {
        if ($node instanceof Node\Stmt\Namespace_) {
            if ($node->name !== null) {
                $this->open($node, 'Namespace', $node->name->toString(), self::fqn($node->name));
            }
        } elseif ($node instanceof Node\Stmt\ClassLike) {
            if ($node->namespacedName !== null) {
                $this->enterClassLike($node);
            }
        } elseif ($node instanceof Node\Stmt\Function_) {
            if ($node->namespacedName !== null) {
                $this->open($node, 'Function', $node->name->toString(), self::fqn($node->namespacedName), [
                    'params' => $this->params($node->params),
                ]);
            }
        } elseif ($node instanceof Node\Stmt\ClassMethod) {
            $this->open($node, 'Method', $node->name->toString(), $this->member($node->name->toString()), [
                'modifiers' => $this->methodModifiers($node),
                'params' => $this->params($node->params),
            ]);
        } else {
            $this->enterMemberOrReference($node);
        }

        return null;
    }

    public function leaveNode(Node $node)
    {
        if ($this->scope[count($this->scope) - 1][0] === $node) {
            array_pop($this->scope);
        }

        return null;
    }

    /** Declarations that contain no members of their own, plus every reference edge. */
    private function enterMemberOrReference(Node $node): void
    {
        if ($node instanceof Node\Stmt\Property) {
            foreach ($node->props as $property) {
                $name = '$' . $property->name->toString();
                $this->declare($property, 'Property', $name, $this->member($name), [
                    'modifiers' => $this->propertyModifiers($node),
                ]);
            }
        } elseif ($node instanceof Node\Stmt\ClassConst) {
            foreach ($node->consts as $const) {
                $name = $const->name->toString();
                $this->declare($const, 'ClassConst', $name, $this->member($name));
            }
        } elseif ($node instanceof Node\Stmt\Use_) {
            foreach ($node->uses as $use) {
                $this->edge('IMPORTS', $this->path, self::fqn($use->name), $use->getStartLine());
            }
        } elseif ($node instanceof Node\Expr\New_ && $node->class instanceof Node\Name) {
            $this->edge('NEW', $this->container(), self::fqn($node->class), $node->getStartLine());
        } elseif ($node instanceof Node\Expr\MethodCall && $node->name instanceof Node\Identifier) {
            // One file cannot know the receiver's type, so never claim RESOLVED here (R5.2).
            $target = $node->name->toString();
            $this->edge('CALLS', $this->container(), $target, $node->getStartLine(), 'HEURISTIC');
        } elseif ($node instanceof Node\Expr\StaticCall
            && $node->class instanceof Node\Name
            && $node->name instanceof Node\Identifier
        ) {
            $target = self::fqn($node->class) . '::' . $node->name->toString();
            $this->edge('CALLS', $this->container(), $target, $node->getStartLine());
        } elseif ($node instanceof Node\Expr\FuncCall && $node->name instanceof Node\Name) {
            $this->edge('CALLS', $this->container(), self::fqn($node->name), $node->getStartLine());
        } elseif ($node instanceof Node\Expr\Include_) {
            $this->enterInclude($node);
        }
    }

    private function enterClassLike(Node\Stmt\ClassLike $node): void
    {
        $qname = self::fqn($node->namespacedName);
        $this->open($node, self::CLASS_LIKE_KINDS[$node::class], $node->name->toString(), $qname, [
            'modifiers' => $this->classModifiers($node),
        ]);

        foreach ($this->parentsOf($node) as $parent) {
            $this->edge('EXTENDS', $qname, self::fqn($parent), $parent->getStartLine());
        }
        foreach ($this->interfacesOf($node) as $interface) {
            $this->edge('IMPLEMENTS', $qname, self::fqn($interface), $interface->getStartLine());
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

    /** Record a declaration and make it the container for everything nested inside it. */
    private function open(Node $node, string $kind, string $name, string $qname, array $extra = []): void
    {
        $this->declare($node, $kind, $name, $qname, $extra);
        $this->scope[] = [$node, $qname];
    }

    private function declare(Node $node, string $kind, string $name, string $qname, array $extra = []): void
    {
        $this->edge('CONTAINS', $this->container(), $qname, $node->getStartLine());
        $this->nodes[] = [
            'kind' => $kind,
            'name' => $name,
            'qualified_name' => $qname,
            'file_path' => $this->path,
            'line_start' => $node->getStartLine(),
            'line_end' => $node->getEndLine(),
        ] + $extra;
    }

    private function edge(string $kind, string $source, string $target, int $line, ?string $tier = null): void
    {
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
        $this->edges[] = $edge;
    }

    private function container(): string
    {
        return $this->scope[count($this->scope) - 1][1];
    }

    private function member(string $name): string
    {
        return $this->container() . '::' . $name;
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
                'type' => $param->type instanceof Node\Name ? self::fqn($param->type) : null,
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
        return array_values(array_keys(array_filter($flags)));
    }

    /** The convention anchors every qualified name at the global namespace. */
    private static function fqn(Node\Name|string $name): string
    {
        return '\\' . ltrim((string) $name, '\\');
    }
}
