/* Example of Python c module with an invalid __text_signature__  */

#include "Python.h"

static PyObject* base_valid(PyObject *self, PyObject* args)
{
    printf("Hello World\n");
    return Py_None;
}

static PyMethodDef base_methods[] = {
    {"coming_from_c_module",             base_valid,      METH_VARARGS,   "coming_from_c_module($self, a='r', b=-3.14)\n"
    "--\n"
    "\n"
    "Function demonstrating a valid __text_signature__ from C code."},
    
    {NULL,              NULL,           0,              NULL}           /* sentinel */
};

static PyModuleDef base_definition = {
    PyModuleDef_HEAD_INIT,
    "base",
    "Dummy c-module.",
    -1,
    base_methods
};

PyObject* PyInit_base(void) {
    Py_Initialize();
    return PyModule_Create(&base_definition);
}
