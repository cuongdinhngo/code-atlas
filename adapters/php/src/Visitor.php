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

    /**
     * Literals a concatenation continues, by ``spl_object_id``: their end does not end the SQL (335).
     *
     * @var array<int, true>
     */
    private array $continuedLiterals = [];

    /** Declared member types for the class-likes in THIS file; empty when nothing collected them. */
    private readonly MemberTypes $members;

    private readonly TypeTable $types;

    public function __construct(
        private readonly string $path,
        int $lineCount,
        private readonly string $source = '',
        private readonly bool $declarationsOnly = false,
        ?MemberTypes $members = null,
    ) {
        $this->members = $members ?? new MemberTypes();
        $this->types = new TypeTable($this->members);
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
                $this->types->beginFunction(null);
                $this->types->bindParams($node->params);
                $this->open($node, 'Function', $node->name->toString(), self::fqn($node->namespacedName), [
                    'params' => $this->params($node->params),
                ] + $this->extraFields($this->callableExtra($node->attrGroups, $node->returnType)));
                $this->emitCallableReferences(
                    $this->container(),
                    $node->params,
                    $node->returnType,
                    $node->attrGroups,
                    $node->getStartLine(),
                );
            }
            if ($this->declarationsOnly) {
                return NodeTraverser::DONT_TRAVERSE_CHILDREN;
            }
        } elseif ($node instanceof Node\Stmt\ClassMethod) {
            $this->stringLocals = [];
            $frame = $this->innermostScope(Node\Stmt\ClassLike::class);
            $this->types->beginFunction($frame === null ? null : $frame[1]);
            $this->types->bindParams($node->params);
            if ($node->name->toString() === '__construct') {
                $this->declarePromotedProperties($node);
            }
            $this->open($node, 'Method', $node->name->toString(), $this->member($node->name->toString()), [
                'modifiers' => $this->methodModifiers($node),
                'params' => $this->params($node->params),
            ] + $this->extraFields($this->callableExtra($node->attrGroups, $node->returnType)));
            $this->emitCallableReferences(
                $this->container(),
                $node->params,
                $node->returnType,
                $node->attrGroups,
                $node->getStartLine(),
            );
            if ($this->declarationsOnly) {
                return NodeTraverser::DONT_TRAVERSE_CHILDREN;
            }
        } elseif ($node instanceof Node\Expr\Closure) {
            $this->stringLocalsStack[] = $this->stringLocals;
            $this->stringLocals = [];
            // `use` is by value unless by reference, and a by-reference capture can be rewritten
            // anywhere the closure is called from, so only the by-value ones stay evidence.
            $this->types->push(inherit: true);
            $this->types->keepOnly($this->byValueUses($node));
            $this->types->bindParams($node->params);
            $this->enterClosureLike($node, 'closure', '{closure}', $node->params, $node->static, $node->attrGroups, $node->returnType);
        } elseif ($node instanceof Node\Expr\ArrowFunction) {
            // fn() auto-captures by value — keep outer bindings; stack still restores on leave.
            $this->stringLocalsStack[] = $this->stringLocals;
            $this->types->push(inherit: true);
            $this->types->bindParams($node->params);
            $this->enterClosureLike($node, 'fn', '{fn}', $node->params, $node->static, $node->attrGroups, $node->returnType);
        } elseif ($node instanceof Node\Expr\Assign) {
            $this->enterAssign($node);
        } elseif ($node instanceof Node\Expr\AssignOp || $node instanceof Node\Expr\AssignRef) {
            $this->forgetStringLocal($node->var);
            $this->types->forget($node->var);
        } elseif ($node instanceof Node\Stmt\Foreach_) {
            $this->forgetStringLocal($node->valueVar);
            $this->types->forget($node->valueVar);
            if ($node->keyVar !== null) {
                $this->forgetStringLocal($node->keyVar);
                $this->types->forget($node->keyVar);
            }
        } elseif ($node instanceof Node\Stmt\Catch_ && $node->var !== null) {
            $this->forgetStringLocal($node->var);
            // `catch (T $e)` declares the type of $e (language.exceptions).
            $this->types->bind(
                is_string($node->var->name) ? $node->var->name : '',
                count($node->types) === 1 ? $this->types->only($node->types[0]) : null,
            );
        } elseif ($node instanceof Node\Stmt\Unset_) {
            foreach ($node->vars as $var) {
                $this->forgetStringLocal($var);
                $this->types->forget($var);
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
            $this->types->pop();
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
        } elseif ($node instanceof Node\Expr\ClassConstFetch) {
            $this->enterClassConstFetch($node);
        } elseif ($node instanceof Node\Expr\StaticPropertyFetch) {
            $this->enterStaticPropertyFetch($node);
        } elseif ($node instanceof Node\Expr\BinaryOp\Concat) {
            // Parents are entered before children, so the left literal is marked before it is read.
            $left = $node->left;
            while ($left instanceof Node\Expr\BinaryOp\Concat) {
                $left = $left->right;
            }
            $this->continuedLiterals[spl_object_id($left)] = true;
        } elseif ($node instanceof Node\Scalar\String_) {
            $this->enterSqlLiteral($node, $node->value, !isset($this->continuedLiterals[spl_object_id($node)]));
        } elseif ($node instanceof Node\Scalar\InterpolatedString
            && ($node->parts[0] ?? null) instanceof Node\InterpolatedStringPart
        ) {
            // Only the literal before the first interpolation is text; a name cut by it is no name.
            $this->enterSqlLiteral($node, $node->parts[0]->value, false);
        }
    }

    /** ``Foo::$bar`` — read or write — uses that property; a dynamic class or name emits nothing (336). */
    private function enterStaticPropertyFetch(Node\Expr\StaticPropertyFetch $node): void
    {
        if (!($node->class instanceof Node\Name) || !($node->name instanceof Node\VarLikeIdentifier)) {
            return;
        }
        $owner = $this->mentionTarget($node->class);
        if ($owner === null) {
            return;
        }
        // static:: binds late, so a subclass may redeclare it — HEURISTIC, as enterStaticCall does.
        $tier = strcasecmp($node->class->toString(), 'static') === 0 ? 'HEURISTIC' : null;
        $this->edge(
            'REFERENCES',
            $this->container(),
            $owner . '::$' . $node->name->toString(),
            $node->getStartLine(),
            $tier,
        );
    }

    /** A literal that begins a T-SQL write or EXEC emits that edge, read from text (335). */
    private function enterSqlLiteral(Node\Scalar $node, string $text, bool $closed): void
    {
        $statement = SqlLiteral::read($text, $closed);
        if ($statement === null) {
            return;
        }
        $doc = [Node\Scalar\String_::KIND_HEREDOC, Node\Scalar\String_::KIND_NOWDOC];
        $heredoc = in_array($node->getAttribute('kind'), $doc, true);
        $line = $node->getStartLine() + ($heredoc ? 1 : 0)
            + substr_count(substr($text, 0, $statement['offset']), "\n");
        $this->edge($statement['kind'], $this->container(), $statement['target'], $line, 'HEURISTIC');
    }

    /** ``Foo::class`` is a textual class mention — not a call and not ``new`` (task 094). */
    private function enterClassConstFetch(Node\Expr\ClassConstFetch $node): void
    {
        if (!($node->class instanceof Node\Name) || !($node->name instanceof Node\Identifier)) {
            return;
        }
        if (strcasecmp($node->name->toString(), 'class') !== 0) {
            return;
        }
        $target = $this->mentionTarget($node->class);
        if ($target === null) {
            return;
        }
        $this->edge(
            'REFERENCES',
            $this->container(),
            $target,
            $node->getStartLine(),
            'DYNAMIC',
        );
    }

    /** self/static/parent name the enclosing class-like, as in enterStaticCall; null → no edge. */
    private function mentionTarget(Node\Name $class): ?string
    {
        $special = strtolower($class->toString());
        if ($special === 'self' || $special === 'static') {
            $frame = $this->innermostScope(Node\Stmt\ClassLike::class);

            return $frame === null ? null : $frame[1];
        }
        if ($special === 'parent') {
            return $this->enclosingParentQname();
        }

        return self::fqn($class);
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
        $this->emitAttributeReferences($qname, $node->attrGroups, $node->getStartLine());

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
        $this->emitAttributeReferences($qname, $node->attrGroups, $node->getStartLine());

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
        ?Node $returnType,
    ): void {
        $fields = ['params' => $this->params($params)];
        if ($static) {
            $fields['modifiers'] = ['static'];
        }
        $fields += $this->extraFields($this->callableExtra($attrGroups, $returnType));
        $this->open($node, 'Function', $name, $this->anonymousQname($node, $anchor), $fields);
        $this->emitCallableReferences(
            $this->container(),
            $params,
            $returnType,
            $attrGroups,
            $node->getStartLine(),
        );
    }

    /**
     * Attributes plus declared return type under ``extra['type']`` (same key as properties; task 144).
     *
     * @param Node\AttributeGroup[] $attrGroups
     *
     * @return array<string, mixed>
     */
    private function callableExtra(array $attrGroups, ?Node $returnType): array
    {
        $extra = $this->attributeExtra($attrGroups);
        if (($type = self::typeName($returnType)) !== null) {
            $extra['type'] = $type;
        }

        return $extra;
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
            $qname = $this->member($name);
            $this->declare($property, 'Property', $name, $qname, [
                'modifiers' => $this->propertyModifiers($node),
            ] + $this->extraFields($extra));
            $this->emitTypeReferences($qname, $node->type, $property->getStartLine());
            $this->emitAttributeReferences($qname, $node->attrGroups, $property->getStartLine());
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
            $qname = $this->member($name);
            $this->declare($const, 'ClassConst', $name, $qname, [
                'modifiers' => $this->classConstModifiers($node),
            ] + $this->extraFields($extra));
            $this->emitTypeReferences($qname, $node->type, $const->getStartLine());
            $this->emitAttributeReferences($qname, $node->attrGroups, $const->getStartLine());
        }
    }

    private function enterEnumCase(Node\Stmt\EnumCase $node): void
    {
        $extra = ['enum_case' => true] + $this->attributeExtra($node->attrGroups);
        $name = $node->name->toString();
        $qname = $this->member($name);
        $this->declare($node, 'ClassConst', $name, $qname, $this->extraFields($extra));
        $this->emitAttributeReferences($qname, $node->attrGroups, $node->getStartLine());
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
        $this->types->observeAssign($node);
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
        } elseif ($fn === 'spl_autoload_register') {
            // Class loading via a registered autoloader emits no INCLUDES — stamp, do not invent edges (279).
            $this->markUnmodelledResolution('autoload');
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
        // $this / $this?-> → the enclosing FQN, which is the class the call was made ON. Whether
        // that class declares $method here or inherits it is the resolver's walk to make (137).
        if ($node->var instanceof Node\Expr\Variable
            && $node->var->name === 'this'
            && ($owner = $this->receiverQnameForThis($method)) !== null
        ) {
            $this->edge(
                'CALLS', $this->container(), $owner . '::' . $method, $node->getStartLine(), null, $node,
            );
            return;
        }
        $owner = $this->types->classOf($node->var);
        if ($owner !== null && $this->canDeclare($owner, $method)) {
            $this->edge(
                'CALLS', $this->container(), $owner . '::' . $method, $node->getStartLine(), null, $node,
            );
            return;
        }
        $this->edge(
            'CALLS', $this->container(), $method, $node->getStartLine(), 'HEURISTIC', $node,
        );
    }

    /**
     * Whether naming ``$class::$method`` is a claim this file can stand behind.
     *
     * A class declared elsewhere is the resolver's to answer. One declared HERE is fully known, so
     * a method it neither declares nor can inherit is reached through `__call` and nothing else —
     * naming it would invent a declaration site that does not exist.
     */
    private function canDeclare(string $class, string $method): bool
    {
        if (!$this->members->knows($class)) {
            return true;
        }

        return $this->members->method($class, $method) !== null || $this->members->inherits($class);
    }

    /**
     * Names a closure captures by value. A by-reference capture can be rewritten by any caller,
     * so its declared type at this point is not evidence about the object it holds later.
     *
     * @return list<string>
     */
    private function byValueUses(Node\Expr\Closure $node): array
    {
        $names = [];
        foreach ($node->uses as $use) {
            if (!$use->byRef && is_string($use->var->name)) {
                $names[] = $use->var->name;
            }
        }

        return $names;
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
            && ($owner = $this->receiverQnameForThis($method)) !== null
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

    /**
     * The class-like `$this->$method()` was called on, or null when naming it would be a guess.
     *
     * Declared right here is always safe. Otherwise only a class or enum that extends, implements
     * or uses something can inherit the method — a trait's `$this` is the *using* class (029 AC2),
     * and a class with no ancestry at all can only reach `$method` through `__call`.
     */
    private function receiverQnameForThis(string $method): ?string
    {
        if (($owner = $this->enclosingDeclaringQname($method)) !== null) {
            return $owner;
        }
        $frame = $this->innermostScope(Node\Stmt\ClassLike::class);
        if ($frame === null) {
            return null;
        }
        $node = $frame[0];
        assert($node instanceof Node\Stmt\ClassLike);

        return self::inherits($node) ? $frame[1] : null;
    }

    /** True when this declaration can inherit a method it does not declare (PHP: OOP inheritance). */
    private static function inherits(Node\Stmt\ClassLike $node): bool
    {
        if (!$node instanceof Node\Stmt\Class_ && !$node instanceof Node\Stmt\Enum_) {
            return false;
        }
        if ($node instanceof Node\Stmt\Class_ && $node->extends !== null) {
            return true;
        }
        if ($node->implements !== []) {
            return true;
        }
        foreach ($node->stmts as $statement) {
            if ($statement instanceof Node\Stmt\TraitUse) {
                return true;
            }
        }

        return false;
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
            $qname = $this->member($name);
            $extra = [];
            if (($type = self::typeName($param->type)) !== null) {
                $extra['type'] = $type;
            }
            $extra += $this->attributeExtra($param->attrGroups);
            $this->declare($param, 'Property', $name, $qname, [
                'modifiers' => $this->promotedModifiers($param->flags),
            ] + $this->extraFields($extra));
            $this->emitTypeReferences($qname, $param->type, $param->getStartLine());
            $this->emitAttributeReferences($qname, $param->attrGroups, $param->getStartLine());
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
        // Anchored on the file, never the enclosing container: an include splices a file in, and
        // the target is already resolved relative to this file's directory, not to a namespace.
        [$target, $tier] = self::includeTarget($node->expr);
        $this->edge('INCLUDES', $this->path, $target, $node->getStartLine(), $tier);
    }

    /**
     * An include's target and tier (353). A literal, or `__DIR__` / `dirname(__DIR__, n)` plus a
     * literal, is includer-relative and exact (the magic constants are language spec). One other
     * head plus a literal `/…` tail is that tail at HEURISTIC: the core links it by a unique path
     * suffix. Anything else is dynamic.
     *
     * @return array{0: string, 1: string|null}
     */
    private static function includeTarget(Node\Expr $expr): array
    {
        $parts = self::concatParts($expr);
        $tail = '';
        while ($parts !== []) {
            $last = $parts[count($parts) - 1];
            if (!$last instanceof Node\Scalar\String_) {
                break;
            }
            array_pop($parts);
            $tail = $last->value . $tail;
        }
        if ($parts === [] && $tail !== '') {
            return [$tail, null];
        }
        if ($parts === [] || strlen($tail) < 2 || $tail[0] !== '/') {
            return ['(dynamic)', 'DYNAMIC'];
        }
        if (count($parts) !== 1) {
            // A variable between the root and the tail leaves the directory unknown, not just the root.
            return ['(dynamic)', 'DYNAMIC'];
        }
        $levels = self::levelsAboveIncluder($parts[0]);
        if ($levels !== null) {
            return [str_repeat('../', $levels) . substr($tail, 1), null];
        }

        return [$tail, 'HEURISTIC'];
    }

    /** @return list<Node\Expr> the operands of a `.` chain, left to right */
    private static function concatParts(Node\Expr $expr): array
    {
        if ($expr instanceof Node\Expr\BinaryOp\Concat) {
            return [...self::concatParts($expr->left), ...self::concatParts($expr->right)];
        }

        return [$expr];
    }

    /** Directories above the includer that `__DIR__`, `dirname(__FILE__)` or `dirname(…, n)` name. */
    private static function levelsAboveIncluder(Node\Expr $head): ?int
    {
        if ($head instanceof Node\Scalar\MagicConst\Dir) {
            return 0;
        }
        if (!$head instanceof Node\Expr\FuncCall || !$head->name instanceof Node\Name
            || $head->isFirstClassCallable() || strtolower($head->name->getLast()) !== 'dirname') {
            return null;
        }
        $args = $head->getArgs();
        if ($args === [] || count($args) > 2 || $args[0]->unpack || $args[0]->name !== null) {
            return null;
        }
        $up = 1;
        if (isset($args[1])) {
            $count = $args[1]->value;
            if (!$count instanceof Node\Scalar\Int_ || $count->value < 1 || $args[1]->name !== null) {
                return null;
            }
            $up = $count->value;
        }
        $inner = $args[0]->value;
        if ($inner instanceof Node\Scalar\MagicConst\File) {
            return $up - 1;
        }
        $below = self::levelsAboveIncluder($inner);

        return $below === null ? null : $below + $up;
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

    /**
     * Named class types on a declaration → REFERENCES (task 232). Scalars emit nothing.
     * Attributes stay in ``extra`` too; this only adds the graph edge Python already emits.
     *
     * @param Node\Param[]          $params
     * @param Node\AttributeGroup[] $attrGroups
     */
    private function emitCallableReferences(
        string $owner,
        array $params,
        ?Node $returnType,
        array $attrGroups,
        int $line,
    ): void {
        $this->emitTypeReferences($owner, $returnType, $line);
        foreach ($params as $param) {
            // Promoted ctor params own their Property REFERENCES; skip the Method duplicate.
            if ($param->flags !== 0) {
                continue;
            }
            $this->emitTypeReferences($owner, $param->type, $param->getStartLine());
            $this->emitAttributeReferences($owner, $param->attrGroups, $param->getStartLine());
        }
        $this->emitAttributeReferences($owner, $attrGroups, $line);
    }

    private function emitTypeReferences(string $owner, ?Node $type, int $line): void
    {
        foreach ($this->typeReferenceTargets($type) as $target) {
            $this->edge('REFERENCES', $owner, $target, $line);
        }
    }

    /**
     * @param Node\AttributeGroup[] $attrGroups
     */
    private function emitAttributeReferences(string $owner, array $attrGroups, int $line): void
    {
        foreach ($attrGroups as $group) {
            foreach ($group->attrs as $attr) {
                $this->edge('REFERENCES', $owner, self::fqn($attr->name), $line);
            }
        }
    }

    /**
     * Class-like targets a declared type names, in source order. Mirrors TypeName::classAlternatives
     * but walks the AST so ``self``/``static``/``parent`` resolve via mentionTarget.
     *
     * @return list<string>
     */
    private function typeReferenceTargets(?Node $type): array
    {
        if ($type === null) {
            return [];
        }
        if ($type instanceof Node\NullableType) {
            return $this->typeReferenceTargets($type->type);
        }
        if ($type instanceof Node\UnionType || $type instanceof Node\IntersectionType) {
            $found = [];
            foreach ($type->types as $part) {
                foreach ($this->typeReferenceTargets($part) as $target) {
                    if (!in_array($target, $found, true)) {
                        $found[] = $target;
                    }
                }
            }

            return $found;
        }
        if ($type instanceof Node\Name) {
            $target = $this->mentionTarget($type);

            return $target === null ? [] : [$target];
        }

        return [];
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
                // PHP casts decimal-integer-like string keys to int — not extract()-able.
                if (self::isDecimalIntegerStringKey($item->key->value)) {
                    continue;
                }
                $keys[] = $item->key->value;
            } elseif ($item->key instanceof Node\Scalar\InterpolatedString) {
                // Interpolated keys are not a fixed string — contribute nothing (063).
                continue;
            }
            // Non-literal keys ($k => …) contribute nothing and do not shift later keys.
        }

        return $keys;
    }

    /**
     * True when PHP would cast this string array key to int (language.types.array).
     */
    private static function isDecimalIntegerStringKey(string $value): bool
    {
        if ($value === '' || $value[0] === '+') {
            return false;
        }
        if ($value === '0' || $value === '-0') {
            return true;
        }

        return (bool) preg_match('/^-?[1-9][0-9]*$/', $value);
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
        $this->imports[] = ['fqn' => $fqn, 'alias' => $alias, 'type' => $type];
        $current = $this->nodes[0]['extra'] ?? [];
        $extra = is_array($current) ? $current : [];
        $extra['imports'] = $this->imports;
        $this->nodes[0]['extra'] = $extra;
    }

    private function markUnmodelledResolution(string $strategy): void
    {
        $current = $this->nodes[0]['extra'] ?? [];
        $extra = is_array($current) ? $current : [];
        $existing = $extra['unmodelled_resolution'] ?? [];
        $list = is_array($existing) ? $existing : [];
        if (!in_array($strategy, $list, true)) {
            $list[] = $strategy;
            sort($list);
        }
        $extra['unmodelled_resolution'] = $list;
        $this->nodes[0]['extra'] = $extra;
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

    private static function typeName(?Node $type): ?string
    {
        return TypeName::of($type);
    }

    /** The convention anchors every qualified name at the global namespace. */
    private static function fqn(Node\Name|string $name): string
    {
        return '\\' . ltrim((string) $name, '\\');
    }
}
