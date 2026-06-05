public class Main {
    public static void deeplyNestedFaultyMethod() throws Exception {
        Thread.sleep(1000);
        throw new RuntimeException("A critical Java error occurred!");
    }

    public static void intermediateMethod() throws Exception {
        deeplyNestedFaultyMethod();
    }

    public static void main(String[] args) {
        System.out.println("Java app starting...");
        try {
            intermediateMethod();
        } catch (Exception e) {
            // This will output a multi-line stacktrace to stderr
            e.printStackTrace(System.err);
        }
    }
}
