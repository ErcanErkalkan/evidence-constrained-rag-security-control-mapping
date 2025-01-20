
import java.util.*;

public class Store {

    private Map<Integer, Set<ShopItem>> items = new HashMap<>();

    // @ public invariant (\forall ShopItem a, b; getAllItems().contains(a) &&
    // getAllItems().contains(b); a.getId() == b.getId() ==>
    // a.getName().equals(b.getName()));
    // @ ensures (\forall ShopItem a; getAllItems().contains(a); item != a ==>
    // \old(getAllItems()).contains(a));
    // @ ensures (\forall ShopItem a; \old(getAllItems()).contains(a);
    // getAllItems().contains(a));
    // @ ensures getItemsById(item.getId()).contains(item);
    // @ ensures getAllItems().contains(item);
    public void addItem(ShopItem item) {
        if (!items.containsKey(item.getId())) {
            items.put(item.getId(), new HashSet<>());
        }
        items.get(item.getId()).add(item);
    }

    public boolean hasItem(ShopItem item) {
        if (!items.containsKey(item.getId())) {
            return false;
        }
        Set<ShopItem> itemSet = items.get(item.getId());
        return itemSet.contains(item);
    }

    // @ ensures (\forall ShopItem a; \result.contains(a);
    // getItemsById(id).contains(a));
    // @ ensures (\forall ShopItem a; getItemsById(id).contains(a);
    // \result.contains(a));
    // @ pure
    public Collection<ShopItem> getItemsById(int id) {
        return items.getOrDefault(id, new HashSet<>());
    }

    // @ ensures (\forall int i; items.keySet().contains(i); (\forall ShopItem a;
    // getItemsById(i).contains(a); \result.contains(a)));
    // @ ensures (\forall ShopItem a; \result.contains(a);
    // getItemsById(a.getId()).contains(a));
    // @ pure
    public Collection<ShopItem> getAllItems() {
        Collection<ShopItem> allItems = new ArrayList<>();
        for (Set<ShopItem> itemSet : items.values()) {
            allItems.addAll(itemSet);
        }

        return allItems;
    }

    /*@
    ensures \result != null;
    ensures (\forall ShopItem a; \result.contains(a); getAllItems().contains(a));
    ensures (\forall ShopItem a; \result.contains(a); a.getName().toLowerCase().contains(text.toLowerCase()));
    ensures \result.size() <= 3;
    ensures \result.size() == 3 || \result.size() == (\sum ShopItem a; getAllItems().contains(a); a.getName().toLowerCase().contains(text.toLowerCase()) ? 1 : 0);
    ensures (\forall ShopItem a; getAllItems().contains(a);
    a.getName().toLowerCase().contains(text.toLowerCase()) ==>
    \result.contains(a) ||
    (\forall ShopItem b; \result.contains(b); a.getValueInCents() >= b.getValueInCents()));
    pure;
    @*/
    public List<ShopItem> findCheapestItems(String text) {
        // filter on name containing text, case-insensitive
        List<ShopItem> res = new ArrayList<>();

        for (var item : getAllItems()) {
            if (item.getName().toLowerCase().contains(text.toLowerCase())) {
                res.add(item);
            }
        }

        // sort by price
        res.sort(new Comparator<ShopItem>() {
            @Override
            public int compare(ShopItem o1, ShopItem o2) {
                return Integer.compare(o1.getValueInCents(), o2.getValueInCents());
            }
        });

        // alternative way to do sort by price, suggested by IntelliJ
        res.sort(Comparator.comparingInt(ShopItem::getValueInCents));

        // extract top 3
        return res.subList(0, Math.min(3, res.size()));
    }

}
