/* Native inlet-classifier samplesort.
 *
 * This is a faithful C port of the pure-Python implementation in sort.py.
 * It sorts a Python list in place using the same stable samplesort:
 * sample splitters, scatter each item into an ordered inlet, then drain
 * inlets left to right. Comparisons go through PyObject_RichCompareBool so
 * any orderable objects work; equal keys keep their input order (stable).
 *
 * The extension is optional. sort.py imports it opportunistically and falls
 * back to the pure-Python code when it is not built, so behaviour is
 * identical either way and only the constant factor changes.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define BASE_CASE 32
#define MAX_INLETS 64
#define OVERSAMPLE 4
#define MIN_INLETS 2

typedef struct {
    PyObject **scratch; /* scratch buffer, length >= n */
    int reverse;        /* compare with Py_GT instead of Py_LT */
    int error;          /* set when a comparison raised */
} Ctx;

/* Return 1 when a should sort before b, 0 otherwise. On a comparison error
 * ctx->error is set and 0 is returned; callers must check ctx->error. */
static inline int
less_than(Ctx *ctx, PyObject *a, PyObject *b)
{
    int r = PyObject_RichCompareBool(a, b, ctx->reverse ? Py_GT : Py_LT);
    if (r < 0) {
        ctx->error = 1;
        return 0;
    }
    return r;
}

static void
insertion_sort(Ctx *ctx, PyObject **a, Py_ssize_t lo, Py_ssize_t hi)
{
    for (Py_ssize_t i = lo + 1; i < hi; i++) {
        PyObject *current = a[i];
        Py_ssize_t j = i;
        while (j > lo && less_than(ctx, current, a[j - 1])) {
            a[j] = a[j - 1];
            j--;
        }
        a[j] = current;
        if (ctx->error) {
            return;
        }
    }
}

static int
is_nondecreasing(Ctx *ctx, PyObject **a, Py_ssize_t lo, Py_ssize_t hi)
{
    for (Py_ssize_t i = lo + 1; i < hi; i++) {
        if (less_than(ctx, a[i], a[i - 1])) {
            return 0;
        }
        if (ctx->error) {
            return 0;
        }
    }
    return 1;
}

/* Stable bottom-up merge sort over a[lo..hi), used as the introsort-style
 * depth-limit fallback and to sort large splitter samples. */
static void
merge_sort(Ctx *ctx, PyObject **a, Py_ssize_t lo, Py_ssize_t hi)
{
    Py_ssize_t n = hi - lo;
    if (n < 2) {
        return;
    }
    PyObject **buf = ctx->scratch;
    for (Py_ssize_t width = 1; width < n; width *= 2) {
        for (Py_ssize_t start = 0; start < n; start += 2 * width) {
            Py_ssize_t mid = start + width;
            if (mid > n) {
                mid = n;
            }
            Py_ssize_t end = start + 2 * width;
            if (end > n) {
                end = n;
            }
            Py_ssize_t i = start, j = mid, k = start;
            while (i < mid && j < end) {
                /* Stable: take left when right is not strictly smaller. */
                if (less_than(ctx, a[lo + j], a[lo + i])) {
                    buf[k++] = a[lo + j++];
                }
                else {
                    buf[k++] = a[lo + i++];
                }
                if (ctx->error) {
                    return;
                }
            }
            while (i < mid) {
                buf[k++] = a[lo + i++];
            }
            while (j < end) {
                buf[k++] = a[lo + j++];
            }
        }
        for (Py_ssize_t t = 0; t < n; t++) {
            a[lo + t] = buf[t];
        }
    }
}

/* Locate the inlet for item: the number of splitters strictly less than it. */
static Py_ssize_t
locate(Ctx *ctx, PyObject *item, PyObject **splitters, Py_ssize_t count)
{
    Py_ssize_t lo = 0, hi = count;
    while (lo < hi) {
        Py_ssize_t mid = (lo + hi) / 2;
        if (less_than(ctx, splitters[mid], item)) {
            lo = mid + 1;
        }
        else {
            hi = mid;
        }
        if (ctx->error) {
            return 0;
        }
    }
    return lo;
}

static void sort_range(Ctx *ctx, PyObject **a, Py_ssize_t lo, Py_ssize_t hi,
                       int depth_limit);

static void
partition_equal(Ctx *ctx, PyObject **a, Py_ssize_t lo, Py_ssize_t hi,
                int depth_limit)
{
    PyObject *pivot = a[lo + (hi - lo) / 2];
    PyObject **scratch = ctx->scratch;
    Py_ssize_t n = hi - lo;
    /* Two passes into scratch keep encounter order within each bucket. */
    Py_ssize_t n_less = 0, n_equal = 0, n_greater = 0;
    for (Py_ssize_t i = lo; i < hi; i++) {
        if (less_than(ctx, a[i], pivot)) {
            n_less++;
        }
        else if (less_than(ctx, pivot, a[i])) {
            n_greater++;
        }
        else {
            n_equal++;
        }
        if (ctx->error) {
            return;
        }
    }
    Py_ssize_t off_less = 0;
    Py_ssize_t off_equal = n_less;
    Py_ssize_t off_greater = n_less + n_equal;
    for (Py_ssize_t i = lo; i < hi; i++) {
        if (less_than(ctx, a[i], pivot)) {
            scratch[off_less++] = a[i];
        }
        else if (less_than(ctx, pivot, a[i])) {
            scratch[off_greater++] = a[i];
        }
        else {
            scratch[off_equal++] = a[i];
        }
        if (ctx->error) {
            return;
        }
    }
    for (Py_ssize_t t = 0; t < n; t++) {
        a[lo + t] = scratch[t];
    }
    if (n_less > 1) {
        sort_range(ctx, a, lo, lo + n_less, depth_limit - 1);
    }
    if (n_greater > 1) {
        sort_range(ctx, a, lo + n_less + n_equal, hi, depth_limit - 1);
    }
}

static void
sort_range(Ctx *ctx, PyObject **a, Py_ssize_t lo, Py_ssize_t hi,
           int depth_limit)
{
    if (ctx->error) {
        return;
    }
    Py_ssize_t n = hi - lo;
    if (n < 2) {
        return;
    }
    if (n <= BASE_CASE) {
        insertion_sort(ctx, a, lo, hi);
        return;
    }
    if (is_nondecreasing(ctx, a, lo, hi) || ctx->error) {
        return;
    }
    if (depth_limit <= 0) {
        merge_sort(ctx, a, lo, hi);
        return;
    }

    Py_ssize_t inlet_count = n / BASE_CASE;
    if (inlet_count < MIN_INLETS) {
        inlet_count = MIN_INLETS;
    }
    if (inlet_count > MAX_INLETS) {
        inlet_count = MAX_INLETS;
    }
    Py_ssize_t sample_size = inlet_count * OVERSAMPLE - 1;
    if (sample_size < inlet_count) {
        sample_size = inlet_count;
    }
    if (sample_size > n) {
        sample_size = n;
    }

    if (sample_size < 2) {
        partition_equal(ctx, a, lo, hi, depth_limit);
        return;
    }

    /* Gather an evenly spaced sample and sort it stably. */
    PyObject *sample[MAX_INLETS * OVERSAMPLE];
    double stride = (double)n / (double)sample_size;
    for (Py_ssize_t i = 0; i < sample_size; i++) {
        Py_ssize_t idx = (Py_ssize_t)((double)i * stride);
        if (idx > n - 1) {
            idx = n - 1;
        }
        sample[i] = a[lo + idx];
    }
    /* Sort the sample in a private buffer via merge_sort's scratch usage:
     * merge_sort operates on a[lo..hi) using ctx->scratch, so run it over a
     * temporary array by pointing at the sample directly. */
    if (sample_size <= 128) {
        insertion_sort(ctx, sample, 0, sample_size);
    }
    else {
        merge_sort(ctx, sample, 0, sample_size);
    }
    if (ctx->error) {
        return;
    }

    Py_ssize_t splitter_count = inlet_count - 1;
    PyObject *splitters[MAX_INLETS];
    Py_ssize_t n_split = 0;
    for (Py_ssize_t rank = 1; rank <= splitter_count; rank++) {
        Py_ssize_t index = (rank * sample_size) / (splitter_count + 1);
        if (index > sample_size - 1) {
            index = sample_size - 1;
        }
        PyObject *candidate = sample[index];
        if (n_split == 0) {
            splitters[n_split++] = candidate;
        }
        else if (less_than(ctx, splitters[n_split - 1], candidate)) {
            splitters[n_split++] = candidate;
        }
        if (ctx->error) {
            return;
        }
    }

    if (n_split == 0) {
        partition_equal(ctx, a, lo, hi, depth_limit);
        return;
    }

    /* Counting scatter into ctx->scratch keeps items stable within inlets. */
    Py_ssize_t inlets = n_split + 1;
    Py_ssize_t counts[MAX_INLETS + 1];
    for (Py_ssize_t b = 0; b < inlets; b++) {
        counts[b] = 0;
    }
    /* Store each item's inlet in the tail of scratch is not safe (overlap),
     * so recompute during placement using a two-pass count. */
    for (Py_ssize_t i = lo; i < hi; i++) {
        Py_ssize_t b = locate(ctx, a[i], splitters, n_split);
        if (ctx->error) {
            return;
        }
        counts[b]++;
    }
    /* Detect the "no real partition" case (one inlet holds everything). */
    Py_ssize_t max_count = 0;
    for (Py_ssize_t b = 0; b < inlets; b++) {
        if (counts[b] > max_count) {
            max_count = counts[b];
        }
    }
    if (max_count == n) {
        partition_equal(ctx, a, lo, hi, depth_limit);
        return;
    }

    Py_ssize_t offsets[MAX_INLETS + 1];
    Py_ssize_t running = 0;
    for (Py_ssize_t b = 0; b < inlets; b++) {
        offsets[b] = running;
        running += counts[b];
    }
    PyObject **scratch = ctx->scratch;
    Py_ssize_t cursor[MAX_INLETS + 1];
    for (Py_ssize_t b = 0; b < inlets; b++) {
        cursor[b] = offsets[b];
    }
    for (Py_ssize_t i = lo; i < hi; i++) {
        Py_ssize_t b = locate(ctx, a[i], splitters, n_split);
        if (ctx->error) {
            return;
        }
        scratch[cursor[b]++] = a[i];
    }
    for (Py_ssize_t t = 0; t < n; t++) {
        a[lo + t] = scratch[t];
    }

    /* Drain each inlet in order, recursing into the ones that need it. */
    for (Py_ssize_t b = 0; b < inlets; b++) {
        Py_ssize_t size = counts[b];
        if (size > 1) {
            Py_ssize_t seg_lo = lo + offsets[b];
            sort_range(ctx, a, seg_lo, seg_lo + size, depth_limit - 1);
            if (ctx->error) {
                return;
            }
        }
    }
}

static int
max_depth(Py_ssize_t n)
{
    int depth = 0;
    while (n > 1) {
        n /= 2;
        depth++;
    }
    return 2 * depth + 8;
}

PyDoc_STRVAR(sort_doc,
"sort(values, reverse=False, /)\n\n"
"Sort the list *values* in place using the native inlet samplesort.\n"
"The sort is stable. Raises TypeError if elements are not orderable.");

static PyObject *
inletsort_sort(PyObject *module, PyObject *args)
{
    (void)module;
    PyObject *list;
    int reverse = 0;
    if (!PyArg_ParseTuple(args, "O|p:sort", &list, &reverse)) {
        return NULL;
    }
    if (!PyList_Check(list)) {
        PyErr_SetString(PyExc_TypeError, "sort() requires a list");
        return NULL;
    }

    Py_ssize_t n = PyList_GET_SIZE(list);
    if (n < 2) {
        Py_RETURN_NONE;
    }

    PyObject **base = PyMem_Malloc((size_t)n * sizeof(PyObject *));
    PyObject **old = PyMem_Malloc((size_t)n * sizeof(PyObject *));
    PyObject **scratch = PyMem_Malloc((size_t)n * sizeof(PyObject *));
    if (base == NULL || old == NULL || scratch == NULL) {
        PyMem_Free(base);
        PyMem_Free(old);
        PyMem_Free(scratch);
        return PyErr_NoMemory();
    }

    /* Hold a reference to every element so reentrant comparisons that mutate
     * the source list cannot free objects out from under us. */
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *item = PyList_GET_ITEM(list, i);
        old[i] = item;
        base[i] = item;
        Py_INCREF(item);
    }

    Ctx ctx = {scratch, reverse, 0};
    sort_range(&ctx, base, 0, n, max_depth(n));

    if (ctx.error) {
        for (Py_ssize_t i = 0; i < n; i++) {
            Py_DECREF(base[i]);
        }
        PyMem_Free(base);
        PyMem_Free(old);
        PyMem_Free(scratch);
        return NULL;
    }

    /* Commit: install sorted references (stealing our holds), then release
     * the list's original references. Both arrays are permutations of the
     * same objects, so the net reference count per object is unchanged. */
    for (Py_ssize_t i = 0; i < n; i++) {
        PyList_SET_ITEM(list, i, base[i]);
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        Py_DECREF(old[i]);
    }

    PyMem_Free(base);
    PyMem_Free(old);
    PyMem_Free(scratch);
    Py_RETURN_NONE;
}

static PyMethodDef inletsort_methods[] = {
    {"sort", inletsort_sort, METH_VARARGS, sort_doc},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef inletsort_module = {
    PyModuleDef_HEAD_INIT,
    "inlet_sort._inletsort",
    "Native inlet-classifier samplesort.",
    -1,
    inletsort_methods,
    NULL,
    NULL,
    NULL,
    NULL,
};

PyMODINIT_FUNC
PyInit__inletsort(void)
{
    return PyModule_Create(&inletsort_module);
}
