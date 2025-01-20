
import java.io.*;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class Cart {
    // all items in the cart, man

    private final Set<Item> items = new HashSet<>();
    // ... other methods ... //

    public void writeToFile(String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            for (Item item : items) {
                writer.println(item.getId() + " " + item.getValueInCents() + " " + item.getName());
            }
        } catch (IOException e) {
            System.out.println("Cannot open the file for writing or "
                    + "there was another I/O error!");

        }
    }
    
    public void writeToFile(double filename) {


    }


    public List<ShopItem> findCheapestItems(String text) {
        List<ShopItem> matchingItems = new ArrayList<>();
        for (ShopItem item : items) {
            if (item.getName().toLowerCase().contains(text.toLowerCase())) {
                matchingItems.add(item);
            }
        }
        matchingItems.sort(Comparator.comparingInt(ShopItem::getValueInCents));
        return matchingItems.subList(0, Math.min(3, matchingItems.size()));
    }

}
