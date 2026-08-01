<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\Modifiers;
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
            } elseif ($node instanceof Node\Stmt\Class_ && $node->name === null) {
                $this->enterAnonymousClass($node);
            }
        } elseif ($node instanceof Node\Stmt\Function_) {
            if ($node->namespacedName !== null) {
                $this->open($node, 'Function', $node->name->toString(), self::fqn($node->namespacedName), [
                    'params' => $this->params($node->params),
                ] + $this->extraFields($this->rawAttributes($node->attrGroups)));
            }
        } elseif ($node instanceof Node\Stmt\ClassMethod) {
            if ($node->name->toString() === '__construct') {
                $this->declarePromotedProperties($node);
            }
            $this->open($node, 'Method', $node->name->toString(), $this->member($node->name->toString()), [
                'modifiers' => $this->methodModifiers($node),
                'params' => $this->params($node->params),
            ] + $this->extraFields($this->rawAttributes($node->attrGroups)));
        } elseif ($node instanceof Node\Expr\Closure) {
            $this->enterClosureLike($node, 'closure', '{closure}', $node->params, $node->static, $node->attrGroups);
        } elseif ($node instanceof Node\Expr\ArrowFunction) {
            $this->enterClosureLike($node, 'fn', '{fn}', $node->params, $node->static, $node->attrGroups);
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
            $this->enterProperty($node);
        } elseif ($node instanceof Node\Stmt\ClassConst) {
            $this->enterClassConst($node);
        } elseif ($node instanceof Node\Stmt\EnumCase) {
            $this->declare($node, 'ClassConst', $node->name->toString(), $this->member($node->name->toString()), [
                'extra' => ['enum_case' => true] + (
                    ($attrs = $this->rawAttributes($node->attrGroups)) !== []
                        ? ['attributes' => $attrs]
                        : []
                ),
            ]);
        } elseif ($node instanceof Node\Stmt\Const_) {
            $this->enterGlobalConst($node);
        } elseif ($node instanceof Node\Stmt\TraitUse) {
            $this->enterTraitUse($node);
        } elseif ($node instanceof Node\Stmt\Use_) {
            $this->enterUse($node->type, $node->uses, null, $node->getStartLine());
        } elseif ($node instanceof Node\Stmt\GroupUse) {
            $this->enterGroupUse($node);
        } elseif ($node instanceof Node\Expr\New_) {
            $this->enterNew($node);
        } elseif ($node instanceof Node\Expr\NullsafeMethodCall && $node->name instanceof Node\Identifier) {
            $this->enterInstanceCall($node, $node->name->toString());
        } elseif ($node instanceof Node\Expr\MethodCall && $node->name instanceof Node\Identifier) {
            $this->enterInstanceCall($node, $node->name->toString());
        } elseif ($node instanceof Node\Expr\StaticCall
            && $node->class instanceof Node\Name
            && $node->name instanceof Node\Identifier
        ) {
            $this->enterNamedCall($node, self::fqn($node->class) . '::' . $node->name->toString());
        } elseif ($node instanceof Node\Expr\FuncCall && $node->name instanceof Node\Name) {
            $this->enterNamedCall($node, self::fqn($node->name));
        } elseif ($node instanceof Node\Expr\Include_) {
            $this->enterInclude($node);
        }
    }

    private function enterClassLike(Node\Stmt\ClassLike $node): void
    {
        $qname = self::fqn($node->namespacedName);
        $extra = [];
        if (($attrs = $this->rawAttributes($node->attrGroups)) !== []) {
            $extra['attributes'] = $attrs;
        }
        if ($node instanceof Node\Stmt\Enum_ && $node->scalarType !== null) {
            $extra['scalar_type'] = self::typeName($node->scalarType);
        }
        $this->open($node, self::CLASS_LIKE_KINDS[$node::class], $node->name->toString(), $qname, [
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
        $qname = $this->anonymousQname('class', $node->getStartLine());
        $this->open($node, 'Class', '{class}', $qname, [
            'modifiers' => $this->classModifiers($node),
        ] + $this->extraFields($this->rawAttributes($node->attrGroups)));

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
        $fields += $this->extraFields($this->rawAttributes($attrGroups));
        $this->open($node, 'Function', $name, $this->anonymousQname($anchor, $node->getStartLine()), $fields);
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
        if (($attrs = $this->rawAttributes($node->attrGroups)) !== []) {
            $extra['attributes'] = $attrs;
        }
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
        if (($attrs = $this->rawAttributes($node->attrGroups)) !== []) {
            $extra['attributes'] = $attrs;
        }
        foreach ($node->consts as $const) {
            $name = $const->name->toString();
            $this->declare($const, 'ClassConst', $name, $this->member($name), [
                'modifiers' => $this->classConstModifiers($node),
            ] + $this->extraFields($extra));
        }
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
                    'trait' => self::fqn($adaptation->trait),
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
    private function enterUse(int $type, array $uses, ?Node\Name $prefix, int $line): void
    {
        foreach ($uses as $use) {
            $name = $prefix === null
                ? $use->name
                : Node\Name::concat($prefix, $use->name);
            $fqn = self::fqn($name);
            $importType = self::IMPORT_TYPES[$use->type !== Node\Stmt\Use_::TYPE_UNKNOWN ? $use->type : $type]
                ?? 'class';
            $this->edge('IMPORTS', $this->path, $fqn, $line);
            $this->appendFileImport($fqn, $use->alias?->toString(), $importType);
        }
    }

    private function enterGroupUse(Node\Stmt\GroupUse $node): void
    {
        $this->enterUse($node->type, $node->uses, $node->prefix, $node->getStartLine());
    }

    private function enterNew(Node\Expr\New_ $node): void
    {
        if ($node->class instanceof Node\Name) {
            $this->edge('NEW', $this->container(), self::fqn($node->class), $node->getStartLine());
        } elseif ($node->class instanceof Node\Stmt\Class_) {
            $target = $this->anonymousQname('class', $node->class->getStartLine());
            $this->edge('NEW', $this->container(), $target, $node->getStartLine());
        } else {
            $this->edge('NEW', $this->container(), '(dynamic)', $node->getStartLine(), 'DYNAMIC');
        }
    }

    private function enterInstanceCall(Node\Expr\CallLike $node, string $method): void
    {
        if ($node->isFirstClassCallable()) {
            return;
        }
        // One file cannot know the receiver's type, so never claim RESOLVED here (R5.2).
        $this->edge('CALLS', $this->container(), $method, $node->getStartLine(), 'HEURISTIC');
    }

    private function enterNamedCall(Node\Expr\CallLike $node, string $target): void
    {
        if ($node->isFirstClassCallable()) {
            return;
        }
        $this->edge('CALLS', $this->container(), $target, $node->getStartLine());
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
            if (($attrs = $this->rawAttributes($param->attrGroups)) !== []) {
                $extra['attributes'] = $attrs;
            }
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

    /** Record a declaration and make it the container for everything nested inside it. */
    private function open(Node $node, string $kind, string $name, string $qname, array $fields = []): void
    {
        $this->declare($node, $kind, $name, $qname, $fields);
        $this->scope[] = [$node, $qname];
    }

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

    private function anonymousQname(string $kind, int $line): string
    {
        return $this->container() . '::{' . $kind . '@' . $line . '}';
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
        return array_values(array_keys(array_filter($flags)));
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

    /** @param array<string, mixed> $extra */
    private function extraFields(array $extra): array
    {
        return $extra === [] ? [] : ['extra' => $extra];
    }

    private function appendFileImport(string $fqn, ?string $alias, string $type): void
    {
        $extra = $this->nodes[0]['extra'] ?? [];
        $extra['imports'][] = ['fqn' => $fqn, 'alias' => $alias, 'type' => $type];
        $this->nodes[0]['extra'] = $extra;
    }

    /** @param list<array<string, mixed>> $items */
    private function appendExtraList(string $qname, string $key, array $items): void
    {
        foreach ($this->nodes as $index => $node) {
            if (($node['qualified_name'] ?? null) !== $qname) {
                continue;
            }
            $extra = $node['extra'] ?? [];
            $extra[$key] = array_merge($extra[$key] ?? [], $items);
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
