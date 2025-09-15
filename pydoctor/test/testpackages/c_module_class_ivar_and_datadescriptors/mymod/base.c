#include <Python.h>
#include <structmember.h>

typedef struct {
    PyObject_HEAD
    int number;  // Dummy member for PyMemberDef
} BaseObject;

static PyObject *
Base_get_value(BaseObject *self, void *closure)
{
    return PyUnicode_FromString("dummy");
}

static PyGetSetDef Base_getsetters[] = {
    {"value", (getter)Base_get_value, NULL, "dummy value", NULL},
    {NULL}
};

static PyMemberDef Base_members[] = {
    {"number", T_INT, offsetof(BaseObject, number), 0, "dummy integer attribute"},
    {NULL}
};

static PyTypeObject BaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "base.Base",
    .tp_basicsize = sizeof(BaseObject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "Dummy Base class with a getter-only data descriptor and a dummy member\n@ivar thing: My list of thing\n@type thing: list[str]",
    .tp_new = PyType_GenericNew,
    .tp_getset = Base_getsetters,
    .tp_members = Base_members,
};

static struct PyModuleDef basemodule = {
    PyModuleDef_HEAD_INIT,
    "base",
    "Example Python C extension module",
    -1,
};

PyMODINIT_FUNC
PyInit_base(void)
{
    PyType_Ready(&BaseType);
    PyObject *m = PyModule_Create(&basemodule);
    PyModule_AddObject(m, "Base", (PyObject *)&BaseType);
    return m;
}