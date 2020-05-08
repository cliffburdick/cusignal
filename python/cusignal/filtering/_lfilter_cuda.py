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

from string import Template

from ..utils._caches import _cupy_kernel_cache


# Custom Cupy raw kernel implementing upsample, filter, downsample operation
# Matthew Nicely - mnicely@nvidia.com
_cupy_lfilter_src = Template(
    """
$header

extern "C" {
    __global__ void _cupy_lfilter(
            const int x_len,
            const int a_len,
            const ${datatype} * __restrict__ x,
            const ${datatype} * __restrict__ a,
            const ${datatype} * __restrict__ b,
            ${datatype} * __restrict__ out) {

        for ( int tid = 0; tid < x_len; tid++) {

            ${datatype} isw {};
            ${datatype} wos {};

            // Create input_signal_windows
            if( tid > ( a_len ) ) {
                for ( int i = 0; i < a_len; i++ ) {
                    isw += x[tid - i] * b[i];
                    wos += out[tid - i] * a[i];
                }
            } else {
                for ( int i = 0; i <= tid; i++ ) {
                    isw += x[tid - i] * b[i];
                    wos += out[tid - i] * a[i];
                }
            }

            isw -= wos;

            out[tid] = isw / a[0];
        }
    }
}
"""
)


class _cupy_lfilter_wrapper(object):
    def __init__(self, grid, block, stream, kernel):
        if isinstance(grid, int):
            grid = (grid,)
        if isinstance(block, int):
            block = (block,)

        self.grid = grid
        self.block = block
        self.stream = stream
        self.kernel = kernel

    def __call__(self, b, a, x, out):

        kernel_args = (
            x.shape[0],
            a.shape[0],
            x,
            a,
            b,
            out,
        )

        self.stream.use()
        self.kernel(self.grid, self.block, kernel_args)


def _get_backend_kernel(
    dtype, grid, block, stream, k_type,
):
    from ..utils.compile_kernels import GPUKernel

    kernel = _cupy_kernel_cache[(dtype, k_type.value)]
    if kernel:
        if k_type == GPUKernel.LFILTER:
            return _cupy_lfilter_wrapper(grid, block, stream, kernel)
        else:
            raise NotImplementedError(
                "No CuPY kernel found for k_type {}, datatype {}".format(
                    k_type, dtype
                )
            )
    else:
        raise ValueError(
            "Kernel {} not found in _cupy_kernel_cache".format(k_type)
        )


def _lfilter_gpu(b, a, x, clamp, cp_stream, autosync):
    from ..utils.compile_kernels import _populate_kernel_cache, GPUKernel

    out = cp.zeros_like(x)

    threadsperblock = 1
    blockspergrid = 1

    _populate_kernel_cache(out.dtype.type, GPUKernel.LFILTER)
    kernel = _get_backend_kernel(
        out.dtype.type,
        blockspergrid,
        threadsperblock,
        cp_stream,
        GPUKernel.LFILTER,
    )

    kernel(b, a, x, out)

    if autosync is True:
        cp_stream.synchronize()

    return out
