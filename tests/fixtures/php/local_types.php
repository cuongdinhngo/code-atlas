<?php
declare(strict_types=1);

namespace App\Types;

abstract class Engine extends Machine
{
    public function start(): void
    {
        // Each of these is declared by an ancestor in another file, so only the graph's own
        // EXTENDS / USES_TRAIT / IMPLEMENTS edges can say where (task 137, scope 2).
        $this->boot(); // parent class
        $this->log();  // trait the parent uses
        $this->run();  // interface the parent implements
    }
}

final class Magic
{
    public function __call(string $name, array $arguments): void
    {
    }

    public function go(): void
    {
        // No parent, no interface, no trait: nothing can declare this but __call, so the
        // receiver is not evidence for a target and the call stays a guess.
        $this->whatever();
    }
}

trait Mixin
{
    public function mix(): void
    {
        // A trait's $this is the using class, which this file cannot name (029 AC2).
        $this->hostMethod();
    }
}

final class Wheel
{
    public function spin(): void
    {
    }

    public function twin(): self
    {
        return $this;
    }
}

final class Garage
{
    private Wheel $spare;

    public function __construct(private Wheel $fitted)
    {
        $this->spare = new Wheel();
    }

    public function pick(): Wheel
    {
        return $this->fitted;
    }

    /** Every call below names Wheel::spin, each from a different thing the spec put in the file. */
    public function service(Wheel $given, Wheel|int $union, Wheel ...$rest): void
    {
        $made = new Wheel();
        $made->spin();          // [new]
        $given->spin();         // [param-hint]
        $this->fitted->spin();  // [promoted]
        $this->spare->spin();   // [typed-property]
        $this->pick()->spin();  // [return-hint]
        $given->twin()->spin(); // [self-return]
        $union->spin();         // [single-class-union]
        $given?->spin();        // [nullsafe]

        foreach ($rest as $each) {
            $each->spin();      // [variadic]
        }

        $given = $this->anything();
        $given->spin();         // [rebound]

        try {
            $made->spin();
        } catch (\RuntimeException $error) {
            $error->getMessage(); // catch declares the type
        }
    }

    /** @return mixed */
    public function anything()
    {
        return null;
    }
}

final class Yard
{
    /**
     * Nothing here can be answered from this file: `issue()` and `chain()` are declared in
     * another one, so the receiver is "whatever they return" and only the graph knows.
     */
    public function collect(Depot $depot): void
    {
        $depot->issue()->boot();     // [cross-file-return]
        $depot->chain()->issue();    // [cross-file-self]
        $held = $depot->issue();
        $held->boot();               // [cross-file-rebind]
        $depot->issue()->spin();     // [cross-file-miss] Machine has no spin(): stays precise
        $depot->untyped()->spin();   // [broken-chain] nothing declared: nothing to walk
        $depot->maybe()->issue();    // [nullable-chain] declared, but not as one type
        $depot->chain()->issue()->boot(); // [cross-file-chain] two steps, both in another file
    }
}

final class Surveyor
{
    /**
     * `Shape` declares no area(): only its subtypes do, which is ordinary code once an
     * `instanceof` has narrowed the parameter. Walking up cannot answer it; walking down can.
     */
    public function measure(Shape $shape): void
    {
        $shape->area(); // [subtype-only]
    }
}
