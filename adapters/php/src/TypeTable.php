<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\Node;

/**
 * Per-function local variable types, and the class an expression evaluates to.
 *
 * Every binding comes from the language spec putting the type in the file: `new X`, a parameter or
 * return hint, a typed property, a constructor-promoted parameter, a `catch` type. Nothing here
 * knows a framework or a repository (R2).
 *
 * Flow-sensitive and deliberately forgetful: a write this cannot read re-opens the variable, so a
 * stale binding can never outlive the assignment that invalidated it.
 */
final class TypeTable
{
    /** @var array<string, string> variable name (no `$`) → class-like FQN */
    private array $locals = [];

    /** @var list<array<string, string>> */
    private array $stack = [];

    /** The class-like `$this` names here, or null outside one. */
    private ?string $self = null;

    /** @var list<?string> */
    private array $selfStack = [];

    /** Guard against a pathological receiver chain; real code nests a handful deep. */
    private const MAX_CHAIN = 32;

    /**
     * A reference this file cannot turn into a type: "whatever `\A::m` was declared to return".
     * A fluent chain nests them — `a()->b()->c()` is three — and the graph walks the whole chain.
     */
    public const TYPE_OF = '()';

    /** Matches the core's walk bound, so the adapter never emits a chain nothing will read. */
    private const MAX_TYPE_OF = 8;

    private int $depth = 0;

    public function __construct(private readonly MemberTypes $members)
    {
    }

    /** A method or function body starts with no locals but its parameters. */
    public function beginFunction(?string $self): void
    {
        $this->locals = [];
        $this->self = $self;
    }

    /** A closure body: `use` brings bindings in by value, so keep them; an arrow fn captures all. */
    public function push(bool $inherit): void
    {
        $this->stack[] = $this->locals;
        $this->selfStack[] = $this->self;
        if (!$inherit) {
            $this->locals = [];
        }
    }

    public function pop(): void
    {
        if ($this->stack !== []) {
            $this->locals = array_pop($this->stack);
        }
        if ($this->selfStack !== []) {
            $this->self = array_pop($this->selfStack);
        }
    }

    /** @param list<string> $names variable names (no `$`) that a closure captures by value */
    public function keepOnly(array $names): void
    {
        $this->locals = array_intersect_key($this->locals, array_flip($names));
    }

    /** @param Node\Param[] $params */
    public function bindParams(array $params): void
    {
        foreach ($params as $param) {
            if (!$param->var instanceof Node\Expr\Variable || !is_string($param->var->name)) {
                continue;
            }
            // A variadic parameter is an array OF the type, never the type (PHP 5.6).
            $this->bind($param->var->name, $param->variadic ? null : $this->only($param->type));
        }
    }

    public function bind(string $name, ?string $class): void
    {
        if ($class === null) {
            unset($this->locals[$name]);

            return;
        }
        $this->locals[$name] = $class;
    }

    public function forget(Node $target): void
    {
        if ($target instanceof Node\Expr\Variable && is_string($target->name)) {
            unset($this->locals[$target->name]);
        }
    }

    /** `$x = <expr>` — bind what the expression evaluates to, or forget what it used to be. */
    public function observeAssign(Node\Expr\Assign $node): void
    {
        if ($node->var instanceof Node\Expr\Variable && is_string($node->var->name)) {
            $this->bind($node->var->name, $this->classOf($node->expr));

            return;
        }
        $this->forget($node->var);
        if ($node->var instanceof Node\Expr\Array_ || $node->var instanceof Node\Expr\List_) {
            foreach ($node->var->items as $item) {
                if ($item !== null) {
                    $this->forget($item->value);
                }
            }
        }
    }

    /** The class-like an expression evaluates to, or null when the file does not say. */
    public function classOf(Node\Expr $expr): ?string
    {
        if ($this->depth >= self::MAX_CHAIN) {
            return null;
        }
        $this->depth++;
        try {
            return $this->evaluate($expr);
        } finally {
            $this->depth--;
        }
    }

    private function evaluate(Node\Expr $expr): ?string
    {
        if ($expr instanceof Node\Expr\Variable) {
            if ($expr->name === 'this') {
                return $this->self;
            }

            return is_string($expr->name) ? ($this->locals[$expr->name] ?? null) : null;
        }
        if ($expr instanceof Node\Expr\New_) {
            return $expr->class instanceof Node\Name ? $this->classNameOf($expr->class) : null;
        }
        if ($expr instanceof Node\Expr\Clone_) {
            return $this->classOf($expr->expr);
        }
        if ($expr instanceof Node\Expr\Assign) {
            return $this->classOf($expr->expr);
        }
        if ($expr instanceof Node\Expr\PropertyFetch || $expr instanceof Node\Expr\NullsafePropertyFetch) {
            return $this->memberType($expr->var, $expr->name, property: true);
        }
        if ($expr instanceof Node\Expr\MethodCall || $expr instanceof Node\Expr\NullsafeMethodCall) {
            return $this->memberType($expr->var, $expr->name, property: false);
        }
        if ($expr instanceof Node\Expr\StaticCall && $expr->name instanceof Node\Identifier) {
            $owner = $this->classNameOf($expr->class);

            return $owner === null ? null : $this->memberOf($owner, $expr->name->toString());
        }
        if ($expr instanceof Node\Expr\FuncCall && $expr->name instanceof Node\Name\FullyQualified) {
            $qname = Qname::of($expr->name);
            $declared = $this->members->functionReturn($qname);
            if ($declared !== null) {
                return $this->resolve($declared, null, null);
            }

            return $this->typeOf($qname);
        }

        return null;
    }

    /** True for a reference that names a member's type rather than a type. */
    public static function isTypeOf(string $reference): bool
    {
        return str_ends_with($reference, self::TYPE_OF);
    }

    /** Defer to the graph, up to the chain length the core will walk. */
    private function typeOf(string $memberQname): ?string
    {
        return substr_count($memberQname, self::TYPE_OF) >= self::MAX_TYPE_OF
            ? null
            : $memberQname . self::TYPE_OF;
    }

    /** A `self` / `static` / `parent` class reference, or a name this file resolved. */
    private function classNameOf(Node|Node\Expr $class): ?string
    {
        if ($class instanceof Node\Name\FullyQualified) {
            return Qname::of($class);
        }
        if ($class instanceof Node\Name) {
            return $this->resolve(strtolower($class->toString()), $this->self, $this->self);
        }

        return $class instanceof Node\Expr ? $this->classOf($class) : null;
    }

    private function memberType(Node\Expr $receiver, Node|string $name, bool $property): ?string
    {
        if (!$name instanceof Node\Identifier) {
            return null;
        }
        $owner = $this->classOf($receiver);
        if ($owner === null) {
            return null;
        }

        return $this->memberOf($owner, ($property ? '$' : '') . $name->toString());
    }

    /**
     * The type of ``$owner::$member``: read here when this file declares it, deferred to the graph
     * when it does not. A class this file knows in full is different from one it has never seen —
     * a member the former does not have is not evidence, and must not become a claim.
     */
    private function memberOf(string $owner, string $member): ?string
    {
        $qname = Qname::member($owner, $member);
        if (!self::isTypeOf($owner) && $this->members->knows($owner)) {
            $found = str_starts_with($member, '$')
                ? $this->members->property($owner, $member)
                : $this->members->method($owner, $member);
            if ($found !== null) {
                return $this->resolve($found['type'], $found['declaredBy'], $owner);
            }
            if (!$this->members->inherits($owner)) {
                return null;
            }
        }

        return $this->typeOf($qname);
    }

    /**
     * A declared type read as a class FQN.
     *
     * `self` is the class that declared the member; `static` is the one it was called on — that is
     * what late static binding means, and it is why a fluent `: static` follows the receiver.
     */
    private function resolve(?string $type, ?string $declaredBy, ?string $receiver): ?string
    {
        $alternatives = TypeName::classAlternatives($type);
        if (count($alternatives) !== 1) {
            return null;
        }
        $only = $alternatives[0];
        if ($only === TypeName::SELF) {
            return $declaredBy;
        }
        if ($only === TypeName::STATIC_) {
            return $receiver;
        }
        if ($only === TypeName::PARENT) {
            return $declaredBy === null ? null : $this->members->extendsOf($declaredBy);
        }

        return $only;
    }

    /** A declared type that names exactly one class, for a parameter or a `catch`. */
    public function only(?Node $type): ?string
    {
        return $this->resolve(TypeName::of($type), $this->self, $this->self);
    }
}
