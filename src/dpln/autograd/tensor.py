from __future__ import annotations

from .utils import invert_permutation

import numpy as np

from typing import (
    List,
    Tuple,
    Union,
    Sequence,
    Callable,
    Optional,
    NamedTuple,
    Dict,
)


class Dependency(NamedTuple):
    tensor: Tensor
    grad_fn: Union[Callable[[np.ndarray, Optional[Dict]], np.ndarray], Callable[[np.ndarray], np.ndarray]]
    meta: Dict = None


Arrayable = Union[float, list, np.ndarray]
Tensorable = Union['Tensor', float, np.ndarray]


def ensure_array(arrayable: Arrayable) -> np.ndarray:
    if isinstance(arrayable, np.ndarray):
        return arrayable
    else:
        return np.array(arrayable)


def ensure_tensor(tensorable: Tensorable) -> Tensor:
    if isinstance(tensorable, Tensor):
        return tensorable
    else:
        return Tensor(tensorable)


class Tensor:
    def __init__(self, data: Arrayable, requires_grad: bool = False, dependencies: List[Dependency] = None) -> None:
        self._data = ensure_array(data)
        self.requires_grad = requires_grad
        self.dependencies = dependencies or []
        self.shape = self.data.shape
        self.grad: Optional[Tensor] = None

        if self.requires_grad:
            self.zero_grad()

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, new: np.ndarray) -> None:
        self._data = new
        # detach gradient if set new datasets
        self.grad = None

    def numpy(self) -> np.ndarray:
        return self.data

    def zero_grad(self) -> None:
        self.grad = Tensor(np.zeros_like(self.data))

    def backward(self, grad: Optional[Tensor] = None) -> None:
        assert self.requires_grad, "called backward on a non-requires-grad tensor"
        assert self.grad is not None, "must call zero_grad before backward"

        if grad is None:
            if self.shape == ():
                grad = Tensor(1)
            else:
                raise RuntimeError(
                    "grad must be specified for non-zero-tensor")
        self.grad.data += grad.data

        for dependency in self.dependencies:
            backward_grad = dependency.grad_fn(grad.data) if dependency.meta is None else dependency.grad_fn(grad.data, dependency.meta)
            dependency.tensor.backward(Tensor(backward_grad))

    def dim(self) -> int:
        """Number of self.datasets dimensions"""
        return self._data.ndim

    def numel(self) -> int:
        """the product of the self.datasets’s dimensions."""
        return self._data.size

    def sum(self) -> Tensor:
        return sum(self)

    def mean(self) -> Tensor:
        return mean(self)

    def transpose(self, dim1: int, dim2: int) -> Tensor:
        return transpose(self, dim1, dim2)

    def permute(self, axes: Union[List, Tuple]) -> Tensor:
        return permute(self, axes)

    def reshape(self, shape):
        return reshape(self, shape)

    def flatten(self):
        return flatten(self)

    @property
    def T(self) -> Tensor:
        return permute(self, list(range(len(self.shape) - 1, -1, -1)))

    def __add__(self, other) -> Tensor:
        """called if `self + other`"""
        return add(self, ensure_tensor(other))

    def __radd__(self, other) -> Tensor:
        """called if `other + self`"""
        return add(ensure_tensor(other), self)

    def __iadd__(self, other) -> Tensor:
        """called if `self += other`"""
        self.data = self.data + ensure_tensor(other).data
        return self

    def __sub__(self, other) -> Tensor:
        """called if `self - other`"""
        return sub(self, ensure_tensor(other))

    def __rsub__(self, other) -> Tensor:
        """called if `other - self`"""
        return sub(ensure_tensor(other), self)

    def __isub__(self, other) -> Tensor:
        """called if `self -= other`"""
        self.data = self.data - ensure_tensor(other).data
        return self

    def __neg__(self) -> Tensor:
        """called if `-self`"""
        return neg(self)

    def __mul__(self, other) -> Tensor:
        """called if `self * other`"""
        return mul(self, ensure_tensor(other))

    def __rmul__(self, other) -> Tensor:
        """called if `other - self`"""
        return mul(ensure_tensor(other), self)

    def __imul__(self, other) -> Tensor:
        """called if `self *= other`"""
        self.data = self.data * ensure_tensor(other).data
        return self

    def __truediv__(self, other) -> Tensor:
        """called if `self / other`"""
        return truediv(self, ensure_tensor(other))

    def __rtruediv__(self, other) -> Tensor:
        """called if `other / self`"""
        return truediv(ensure_tensor(other), self)

    def __itruediv__(self, other) -> Tensor:
        """called if `self /= other`"""
        self.data = self.data / ensure_tensor(other).data
        return self

    def __matmul__(self, other) -> Tensor:
        """called if `self @ other`"""
        return matmul(self, ensure_tensor(other))

    def __rmatmul__(self, other) -> Tensor:
        """called if `other @ self`"""
        return matmul(ensure_tensor(other), self)

    def __imatmul__(self, other) -> Tensor:
        """called if `self @= other`"""
        self.data = self.data @ ensure_tensor(other).data
        return self

    def __pow__(self, n):
        """called if `self ** other`"""
        return power(self, ensure_tensor(n))

    def __eq__(self, other: object) -> bool:
        """test if `self == other`"""
        if not isinstance(other, Tensor):
            return NotImplemented
        if self.data.shape != other.data.shape:
            return False
        return (self.data == other.data).all()

    def __getitem__(self, idxs):
        return _slice(self, idxs)

    def __repr__(self) -> str:
        return f"Tensor({self.data}, shape={self.shape}, requires_grad={self.requires_grad})"

    def __hash__(self):
        return hash(str(self.data.data))


def zeros(shape, dtype=None, order='C', requires_grad=False) -> Tensor:
    return Tensor(np.zeros(shape=shape, dtype=dtype, order=order), requires_grad=requires_grad)


def zeros_like(a, dtype=None, order='K', subok=True, shape=None, requires_grad=False) -> Tensor:
    return Tensor(np.zeros_like(a=a, dtype=dtype, order=order, subok=subok, shape=shape), requires_grad=requires_grad)


def ones(shape, dtype=None, order='C', requires_grad=False) -> Tensor:
    return Tensor(np.ones(shape=shape, dtype=dtype, order=order), requires_grad=requires_grad)


def ones_like(a: Tensor, dtype=None, requires_grad=False) -> Tensor:
    if dtype is None:
        dtype = a.data.dtype
    return Tensor(np.ones_like(a=a, dtype=dtype, shape=a.shape), requires_grad=requires_grad)


def _slice(t: Tensor, idxs) -> Tensor:
    # TODO: test
    data = t.data[idxs]
    requires_grad = t.requires_grad
    dependencies: List[Dependency] = []

    if requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            bigger_grad = np.zeros_like(data)
            bigger_grad[idxs] = grad
            return bigger_grad

        dependencies.append(Dependency(t, grad_fn))

    return Tensor(data, requires_grad, dependencies)


def reshape(t: Tensor, shape) -> Tensor:
    data = t.data.reshape(shape)
    requires_grad = t.requires_grad
    dependencies: List[Dependency] = []

    if t.requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            return grad.reshape(t.shape)

        dependencies.append(Dependency(t, grad_fn))

    return Tensor(data, requires_grad, dependencies)


def flatten(t: Tensor) -> Tensor:
    data = t.data.flatten()
    requires_grad = t.requires_grad
    dependencies: List[Dependency] = []

    if t.requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            return grad.reshape(t.shape)

        dependencies.append(Dependency(t, grad_fn))

    return Tensor(data, requires_grad, dependencies)


def concat(tensors: Sequence[Tensor], axis: int = 0) -> Tensor:
    assert len(tensors) > 0
    dim = tensors[0].dim()
    data = np.concatenate([t.data for t in tensors], axis=axis)
    requires_grad = True in [t.requires_grad for t in tensors]
    dependencies: List[Dependency] = []

    a = 0
    b = 0
    for i, t in enumerate(tensors):
        b += tensors[i].shape[axis]
        if t.requires_grad:
            def grad_fn(grad: np.ndarray, meta=None) -> np.ndarray:
                idx = tuple([np.s_[meta["a"]:meta["b"]] if j == axis else np.s_[:] for j in range(dim)])
                return grad[idx]

            dependencies.append(Dependency(t, grad_fn, meta={"a": a, "b": b}))
        a += tensors[i].shape[axis]

    return Tensor(data, requires_grad, dependencies)


def sum(t: Tensor) -> Tensor:
    # TODO: test, support axis param
    """
    Takes a tensor and return the sum of its components
    """
    data = t.data.sum()
    requires_grad = t.requires_grad
    dependencies: List[Dependency] = []

    if requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            return grad * np.ones_like(t.data)

        dependencies.append(Dependency(t, grad_fn))

    return Tensor(data, requires_grad, dependencies)


def mean(t: Tensor) -> Tensor:
    # TODO: test, support axis param
    return t.sum() / t.numel()


def add(t1: Tensor, t2: Tensor) -> Tensor:
    data = np.add(t1.data, t2.data)
    requires_grad = t1.requires_grad or t2.requires_grad
    dependencies: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            ndims_added = grad.ndim - t1.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t1.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t1, grad_fn1))

    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            ndims_added = grad.ndim - t2.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t2.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t2, grad_fn2))

    return Tensor(data, requires_grad, dependencies)


def sub(t1: Tensor, t2: Tensor) -> Tensor:
    data = t1.data - t2.data
    requires_grad = t1.requires_grad or t2.requires_grad
    dependencies: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            ndims_added = grad.ndim - t1.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t1.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t1, grad_fn1))

    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            ndims_added = grad.ndim - t2.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t2.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return -grad

        dependencies.append(Dependency(t2, grad_fn2))

    return Tensor(data, requires_grad, dependencies)


def neg(t: Tensor) -> Tensor:
    data = np.negative(t.data)
    requires_grad = t.requires_grad
    dependencies: List[Dependency] = []

    if requires_grad:
        dependencies.append(Dependency(t, lambda x: -x))

    return Tensor(data, requires_grad, dependencies)


def mul(t1: Tensor, t2: Tensor) -> Tensor:
    data = t1.data * t2.data
    requires_grad = t1.requires_grad or t2.requires_grad
    dependencies: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            grad = grad * t2.data
            ndims_added = grad.ndim - t1.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t1.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t1, grad_fn1))

    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            grad = grad * t1.data
            ndims_added = grad.ndim - t2.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t2.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t2, grad_fn2))

    return Tensor(data, requires_grad, dependencies)


def truediv(t1: Tensor, t2: Tensor) -> Tensor:
    # TODO: fix epsilon
    data = np.divide(t1.data, t2.data)
    requires_grad = t1.requires_grad or t2.requires_grad
    dependencies: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            grad = np.divide(grad, t2.data)
            ndims_added = grad.ndim - t1.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t1.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t1, grad_fn1))

    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            grad = - (grad / t2.data) * (t1.data / t2.data)
            # grad = np.negative(np.divide(np.multiply(grad, t1.datasets), t2.datasets * t2.datasets))
            # grad = np.negative(np.divide(np.multiply(grad, t1.datasets), np.power(t2.datasets, 2)))
            ndims_added = grad.ndim - t2.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(t2.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(t2, grad_fn2))

    return Tensor(data, requires_grad, dependencies)


def matmul(t1: Tensor, t2: Tensor) -> Tensor:
    """
    if t1 is (n1, m1) and t2 is (m1, m2), then t1 @ t2 is (n1, m2)
    so grad3 is (n1, m2)
    if t3 = t1 @ t2, and grad3 is the gradient of some function wrt t3, then
        grad1 = grad3 @ t2.T
        grad2 = t1.T @ grad3
    """
    data = t1.data @ t2.data
    requires_grad = t1.requires_grad or t2.requires_grad
    dependencies: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            return grad @ np.swapaxes(t2.data, -1, -2)

        dependencies.append(Dependency(t1, grad_fn1))

    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            return np.swapaxes(t1.data, -1, -2) @ grad

        dependencies.append(Dependency(t2, grad_fn2))

    return Tensor(data, requires_grad, dependencies)


def power(x: Tensor, e: Tensor) -> Tensor:
    # TODO: fix epsilon
    data = np.power(x.data, e.data)
    requires_grad = x.requires_grad or e.requires_grad
    dependencies: List[Dependency] = []

    if x.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            grad = grad * e.data * np.power(x.data, e.data - 1)
            ndims_added = grad.ndim - x.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(x.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(x, grad_fn1))

    if e.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            grad = grad * data * np.log(x.data)
            ndims_added = grad.ndim - e.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis=0)
            for i, dim in enumerate(e.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims=True)
            return grad

        dependencies.append(Dependency(e, grad_fn2))

    return Tensor(data, requires_grad, dependencies)


def dot(t1: Tensor, t2: Tensor) -> Tensor:
    # TODO: impl, test
    assert t1.dim() <= 1 and t2.dim() <= 1
    data = np.dot(t1.data, t2.data)
    requires_grad = t1.requires_grad or t2.requires_grad
    dependencies: List[Dependency] = []

    return Tensor(data, requires_grad, dependencies)


def transpose(a: Tensor, dim1: int, dim2: int) -> Tensor:
    data = np.swapaxes(a.data, dim1, dim2)
    requires_grad = a.requires_grad
    dependencies: List[Dependency] = []

    if a.requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            return np.swapaxes(grad, dim2, dim1)

        dependencies.append(Dependency(a, grad_fn))

    return Tensor(data, requires_grad, dependencies)


def permute(a: Tensor, axes: Union[List, Tuple]) -> Tensor:
    data = a.data.transpose(axes)
    requires_grad = a.requires_grad
    dependencies: List[Dependency] = []

    if a.requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            axes_t = invert_permutation(axes)
            return grad.transpose(axes_t)

        dependencies.append(Dependency(a, grad_fn))

    return Tensor(data, requires_grad, dependencies)
