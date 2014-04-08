# Copyright (C) 2012  Alex Nitz
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#
import numpy
import events
from scipy.weave import inline

def threshold_numpy(series, value):
    arr = series.data
    locs = numpy.where(arr.real**2 + arr.imag**2 > value**2)[0]
    vals = arr[locs]
    return locs, vals

outl = outv = count = None
def threshold_inline(series, value):
    arr = numpy.array(series.data.view(dtype=numpy.float32), copy=False)
    global outl, outv, count
    if outl is None:
        outl = numpy.zeros(len(series), dtype=numpy.uint32)
        outv = numpy.zeros(len(series), dtype=series.dtype)
        count = numpy.zeros(1, dtype=numpy.uint32)
        
    N = len(series)
    threshold = value**2.0
    code = """  
        float v = threshold;
        int num = 8;
        unsigned int t=0;
     
        #pragma omp parallel for ordered shared(t)
        for (unsigned int p=0; p<num; p++){
            int start  = N * p / num;
            int end    = N * (p+1) / num;
            unsigned int c = 0;
            
            for (unsigned int i=start; i<end; i++){
                float r = arr[i*2];
                float im = arr[i*2+1];
                if ((r * r + im * im > v)){
                    outl[c+start] = i;
                    outv[c+start] = std::complex<float>(r, im);
                    c++;
                }
            } 
            
            #pragma omp ordered
            {
                t+=c;
            }
            memcpy(outl+t-c, outl+start, sizeof(unsigned int)*c);
            memcpy(outv+t-c, outv+start, sizeof(std::complex<float>)*c);
            
        }       
        
        count[0] = t;
    """
    inline(code, ['N', 'arr', 'outv', 'outl', 'count', 'threshold'],
           extra_compile_args=['-march=native  -Ofast  -fopenmp'],
           libraries=['gomp'])
    return outl[0:count], outv[0:count]

threshold=threshold_inline
