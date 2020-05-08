# Copyright (c) 2019-2020, NVIDIA CORPORATION.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cupy as cp
import numpy as np

from enum import Enum

from ._caches import _cupy_kernel_cache

from ..filtering._lfilter_cuda import (
    _cupy_lfilter_src
)
from ..convolution._convolution_cuda import (
    _cupy_convolve_src,
    _cupy_convolve_2d_src,
)
from ..convolution._convolution_cuda import (
    _cupy_correlate_src,
    _cupy_correlate_2d_src,
)
from ..spectral_analysis._spectral_cuda import (
    _cupy_lombscargle_src,
)

from ..filtering._upfirdn_cuda import (
    _cupy_upfirdn_1d_src,
    _cupy_upfirdn_2d_src,
)


class GPUKernel(Enum):
    CORRELATE = 'correlate'
    CONVOLVE = 'convolve'
    CORRELATE2D = 'correlate2d'
    CONVOLVE2D = 'convolve2d'
    LFILTER = 'lfilter'
    LOMBSCARGLE = 'lombscargle'
    UPFIRDN = 'upfirdn'
    UPFIRDN2D = 'upfirdn2d'


# Numba type supported and corresponding C type
_SUPPORTED_TYPES_CONVOLVE = {
    np.int32: "int",
    np.int64: "long int",
    np.float32: "float",
    np.float64: "double",
    np.complex64: "complex<float>",
    np.complex128: "complex<double>",
}

_SUPPORTED_TYPES_LFILTER = {
    np.float32: "float",
    np.float64: "double",
}

_SUPPORTED_TYPES_LOMBSCARGLE = {
    np.float32: "float",
    np.float64: "double",
}

_SUPPORTED_TYPES_UPFIRDN = {
    np.float32: "float",
    np.float64: "double",
    np.complex64: "complex<float>",
    np.complex128: "complex<double>",
}


def _get_supported_types(k_type):

    if (
        k_type == GPUKernel.CORRELATE
        or k_type == GPUKernel.CONVOLVE
        or k_type == GPUKernel.CORRELATE2D
        or k_type == GPUKernel.CONVOLVE2D
    ):
        SUPPORTED_TYPES = _SUPPORTED_TYPES_CONVOLVE

    elif k_type == GPUKernel.LFILTER:
        SUPPORTED_TYPES = _SUPPORTED_TYPES_LFILTER

    elif k_type == GPUKernel.LOMBSCARGLE:
        SUPPORTED_TYPES = _SUPPORTED_TYPES_LOMBSCARGLE

    elif k_type == GPUKernel.UPFIRDN or k_type == GPUKernel.UPFIRDN2D:
        SUPPORTED_TYPES = _SUPPORTED_TYPES_UPFIRDN

    else:
        raise ValueError("Support not found for '{}'".format(k_type.value))

    return SUPPORTED_TYPES


def _validate_input(dtype, k_type):

    k_type = list([k_type]) if k_type else list(GPUKernel)

    for k in k_type:

        # Point to types allowed for kernel
        SUPPORTED_TYPES = _get_supported_types(k)

        d = list(dtype) if dtype else SUPPORTED_TYPES.keys()

        for np_type in d:

            print("n", np_type)

            # Check dtypes from user input
            try:
                SUPPORTED_TYPES[np_type]

            except KeyError:
                raise KeyError(
                    "Datatype {} not found for '{}'".format(np_type, k.value)
                )

            _populate_kernel_cache(np_type, k)


def _populate_kernel_cache(np_type, k_type):

    print("np", str(np_type))

    SUPPORTED_TYPES = _get_supported_types(k_type)

    c_type = SUPPORTED_TYPES[np_type]

    if (np_type, k_type.value) in _cupy_kernel_cache:
        return

    print("hey")

    # Instantiate the cupy kernel for this type and compile
    if (c_type.find('complex') != -1):
        header = "#include <cupy/complex.cuh>"
    else:
        header = ""

    if k_type == GPUKernel.CORRELATE:
        src = _cupy_correlate_src.substitute(
            datatype=c_type, header=header
        )
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_correlate")

    elif k_type == GPUKernel.CONVOLVE:
        src = _cupy_convolve_src.substitute(datatype=c_type, header=header)
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_convolve")

    elif k_type == GPUKernel.CORRELATE2D:
        src = _cupy_correlate_2d_src.substitute(
            datatype=c_type, header=header
        )
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_correlate_2d")

    elif k_type == GPUKernel.CONVOLVE2D:
        src = _cupy_convolve_2d_src.substitute(
            datatype=c_type, header=header
        )
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_convolve_2d")

    elif k_type == GPUKernel.LOMBSCARGLE:
        src = _cupy_lombscargle_src.substitute(
            datatype=c_type, header=header
        )
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_lombscargle")
    elif k_type == GPUKernel.LFILTER:
        src = _cupy_lfilter_src.substitute(datatype=c_type, header=header)
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_lfilter")
    elif k_type == GPUKernel.UPFIRDN:
        src = _cupy_upfirdn_1d_src.substitute(
            datatype=c_type, header=header
        )
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_upfirdn_1d")
    elif k_type == GPUKernel.UPFIRDN2D:
        src = _cupy_upfirdn_2d_src.substitute(
            datatype=c_type, header=header
        )
        module = cp.RawModule(
            code=src, options=("-std=c++11", "-use_fast_math")
        )
        _cupy_kernel_cache[
            (np_type, k_type.value)
        ] = module.get_function("_cupy_upfirdn_2d")

    else:
        raise NotImplementedError(
            "No kernel found for k_type {}, datatype {}".format(
                k_type, np_type
            )
        )


def precompile_kernels(k_type=None, dtype=None):
    r"""
    Precompile GPU kernels for later use.

    Note: If a specified kernel + data type combination at runtime
    does not match any precompiled kernels, it will be compile at
    first call (if kernel and data type combination exist)

    Parameters
    ----------
    k_type : {str}, optional
        Which GPU kernel to compile for. If not specified,
        all supported kernels will be precompiled.
            'correlate'
            'convolve'
            'correlate2d'
            'convolve2d'
            'lfilter'
            'lombscargle'
            'upfirdn'
            'upfirdn2d'
    dtype : dtype or list of dtype, optional
        Data types for which kernels should be precompiled. If not
        specified, all supported data types will be precompiled.
            'correlate'
            'convolve'
            'correlate2d'
            'convolve2d'
            {
                np.int32
                np.int64
                np.float32
                np.float64
                np.complex64
                np.complex128
            }
            'lfilter'
            'lombscargle'
            {
                np.float32
                np.float64
            }
            'upfirdn'
            'upfirdn2d'
            {
                np.float32
                np.float64
                np.complex64
                np.complex128
            }

    Examples
    ----------
    To precompile all kernels
    >>> import cusignal
    >>> cusignal.precompile_kernels()

    To precompile a specific kernel and dtype [list of dtype],
    >>> cusignal.precompile_kernels('lfilter', [np.float32, np.float64])

    To precompile a specific kernel and all data types
    >>> cusignal.precompile_kernels('lfilter')

    To precompile a specific data type and all kernels
    >>> cusignal.precompile_kernels(dtype=[np.float64])

    To precompile a multiple kernels
    >>> cusignal.precompile_kernels('lfilter', [np.float64])
    >>> cusignal.precompile_kernels('correlate', [np.float64])
    """

    if k_type is not None and not isinstance(k_type, str):
        raise TypeError(
            "k_type is type ({}), should be (string) - e.g {}".format(
                type(k_type), "'lfilter'"
            )
        )
    elif k_type is not None:
        k_type = k_type.lower()
        try:
            k_type = GPUKernel(k_type)

        except ValueError:
            raise

    if dtype is not None and not hasattr(dtype, "__iter__"):
        raise TypeError(
            "dtype ({}) should be in list - e.g [np.float32,]".format(dtype)
        )
    else:
        _validate_input(dtype, k_type)
