public class ExampleClass extends A {

    public int a() {
        return b();
    }
    
    private final int b() {
        return c();
    }

    protected static int c() {
        return 4;
    }

    public final static void main(String[] args) {
        A ex = (A) new ExampleClass();
        ((ExampleClass)ex).b();
    }
}
