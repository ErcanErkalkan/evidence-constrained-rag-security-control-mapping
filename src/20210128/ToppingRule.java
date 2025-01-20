import java.util.Collection;

public interface ToppingRule {
  double apply(Collection<Topping> toppings, double value);

}
