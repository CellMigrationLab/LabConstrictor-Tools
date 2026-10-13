import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;
import java.nio.ByteOrder;
import java.util.Random;

/** Java 21 FFM (preview in 21, final in 22): shm_open + ftruncate + mmap straight from libc, no JNA, no JNI. POSIX only. */
public class ShmProofFfm {
    public static void main(String[] args) throws Throwable {
        int side = Integer.getInteger("side", 4096);
        long nbytes = (long) side * side * 2;
        Linker linker = Linker.nativeLinker();
        SymbolLookup libc = linker.defaultLookup();
        // shm_open is variadic (mode is optional): declare the variadic part explicitly
        MethodHandle shmOpen = linker.downcallHandle(libc.find("shm_open").orElseThrow(),
            FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS, ValueLayout.JAVA_INT, ValueLayout.JAVA_INT),
            Linker.Option.firstVariadicArg(2));
        MethodHandle ftruncate = linker.downcallHandle(libc.find("ftruncate").orElseThrow(),
            FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.JAVA_INT, ValueLayout.JAVA_LONG));
        MethodHandle mmap = linker.downcallHandle(libc.find("mmap").orElseThrow(),
            FunctionDescriptor.of(ValueLayout.ADDRESS, ValueLayout.ADDRESS, ValueLayout.JAVA_LONG, ValueLayout.JAVA_INT,
                ValueLayout.JAVA_INT, ValueLayout.JAVA_INT, ValueLayout.JAVA_LONG));
        MethodHandle shmUnlink = linker.downcallHandle(libc.find("shm_unlink").orElseThrow(),
            FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS));
        String name = "/lc_ffm_" + ProcessHandle.current().pid();
        try (Arena arena = Arena.ofConfined()) {
            int fd = (int) shmOpen.invokeExact(arena.allocateUtf8String(name), 02 | 0100, 0600);   // O_RDWR | O_CREAT
            if (fd < 0) throw new IllegalStateException("shm_open failed");
            if ((int) ftruncate.invokeExact(fd, nbytes) != 0) throw new IllegalStateException("ftruncate failed");
            MemorySegment base = (MemorySegment) mmap.invokeExact(MemorySegment.NULL, nbytes, 3, 1, fd, 0L); // PROT_RW, MAP_SHARED
            MemorySegment block = base.reinterpret(nbytes);
            Random r = new Random(1);
            int max = 0; long sum = 0; int first = -1;
            long t0 = System.nanoTime();
            ValueLayout.OfShort le = ValueLayout.JAVA_SHORT.withOrder(ByteOrder.nativeOrder());
            for (long i = 0; i < (long) side * side; i++) {
                int v = r.nextInt(65536);
                max = Math.max(max, v); sum += v; if (first < 0) first = v;
                block.setAtIndex(le, i, (short) v);
            }
            double fill = (System.nanoTime() - t0) / 1e9;
            System.out.println("{\"mode\":\"ffm\",\"name\":\"" + name.substring(1) + "\",\"shape\":[" + side + "," + side
                + "],\"dtype\":\"uint16\",\"max\":" + max + ",\"sum\":" + sum + ",\"first\":" + first + ",\"fill_s\":" + fill + "}");
            System.out.flush();
            System.in.read();
            int rc = (int) shmUnlink.invokeExact(arena.allocateUtf8String(name));
        }
    }
}
