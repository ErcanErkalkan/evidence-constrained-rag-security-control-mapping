import java.util.Collection;

public class TwoToppingsRule implements ToppingRule {

  private final Topping topping1;
  private final Topping topping2;
  private final double modifier;

  public TwoToppingsRule(Topping topping1, Topping topping2, double modifier) {
    this.topping1 = topping1;
    this.topping2 = topping2;
    this.modifier = modifier;
  }

  @Override
  public double apply(Collection<Topping> toppings, double value) {
    if (toppings.contains(topping1) && toppings.contains(topping2)) {
      value = value * modifier;
    }
    return value;
  }

}
