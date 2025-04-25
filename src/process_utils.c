#include <Python.h>
#include <unistd.h>
#include <sys/wait.h>
#include <signal.h>
#include <stdlib.h>

/*
 * Create a new process using fork() system call
 * Returns: Child PID to parent, 0 to child, -1 on error
 */
static PyObject* process_utils_fork(PyObject* self, PyObject* args) {
    pid_t pid = fork();
    
    if (pid < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Fork failed");
        return NULL;
    }
    
    return PyLong_FromLong(pid);
}

/*
 * Wait for a child process to terminate
 * Returns: Child's PID and exit status
 */
static PyObject* process_utils_wait(PyObject* self, PyObject* args) {
    int pid, status;
    
    if (!PyArg_ParseTuple(args, "i", &pid)) {
        return NULL;
    }
    
    if (waitpid(pid, &status, 0) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Wait failed");
        return NULL;
    }
    
    if (WIFEXITED(status)) {
        return Py_BuildValue("ii", pid, WEXITSTATUS(status));
    } else {
        return Py_BuildValue("ii", pid, -1);
    }
}

/*
 * Get current process ID
 */
static PyObject* process_utils_getpid(PyObject* self, PyObject* args) {
    return PyLong_FromLong(getpid());
}

// Module method definitions
static PyMethodDef ProcessUtilsMethods[] = {
    {"fork", process_utils_fork, METH_NOARGS, "Create a new process using fork()"},
    {"wait", process_utils_wait, METH_VARARGS, "Wait for a child process to terminate"},
    {"getpid", process_utils_getpid, METH_NOARGS, "Get current process ID"},
    {NULL, NULL, 0, NULL} // Sentinel
};

// Module definition
static struct PyModuleDef process_utils_module = {
    PyModuleDef_HEAD_INIT,
    "process_utils",
    "Process creation and management utilities using system calls",
    -1,
    ProcessUtilsMethods
};

// Initialize the module
PyMODINIT_FUNC PyInit_process_utils(void) {
    return PyModule_Create(&process_utils_module);
} 