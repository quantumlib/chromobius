"""Chromobius (Development Version): an implementation of the mobius color code decoder."""
# (This a stubs file describing the classes and methods in stim.)
from __future__ import annotations
from typing import overload, TYPE_CHECKING, Any, Iterable
if TYPE_CHECKING:
    import io
    import pathlib
    import numpy as np
    import stim
    import sinter
    import chromobius
__version__: str
class CompiledDecoder:
    """A chromobius decoder ready to predict observable flips from detection events.

    Example:
        >>> import stim
        >>> import chromobius

        >>> dem = stim.Circuit('''
        ...     X_ERROR(0.1) 0 1 2 3 4 5 6 7
        ...     MPP Z0*Z1*Z2 Z1*Z2*Z3 Z2*Z3*Z4 Z3*Z4*Z5
        ...     DETECTOR(0, 0, 0, 1) rec[-4]
        ...     DETECTOR(1, 0, 0, 2) rec[-3]
        ...     DETECTOR(2, 0, 0, 0) rec[-2]
        ...     DETECTOR(3, 0, 0, 1) rec[-1]
        ...     M 0
        ...     OBSERVABLE_INCLUDE(0) rec[-1]
        ... ''').detector_error_model()

        >>> decoder = chromobius.CompiledDecoder.from_dem(dem)
    """
    @staticmethod
    def from_dem(
        dem: stim.DetectorErrorModel,
    ) -> chromobius.CompiledDecoder:
        """Compiles a decoder for a stim detector error model.

        Args:
            dem: A stim detector error model. The detector error model must satisfy:
                1. Basis+Color annotations. Every detector that appears in an error
                    must specify coordinate data including a fourth coordinate. The 4th
                    coordinate indicates the basis and color of the detector with the
                    convention:
                        0 = Red X
                        1 = Green X
                        2 = Blue X
                        3 = Red Z
                        4 = Green Z
                        5 = Blue Z
                        -1 = Ignore this Detector
                2. Rainbow triplets. Bulk errors with three symptoms in one basis should
                    have one symptom of each color. Errors with three symptoms that
                    repeat a color will cause an exception unless they can be decomposed
                    into other basic errors.
                3. Movable excitations. It needs to be possible to combine bulk errors
                    to form simpler errors with one or two symptoms that can be used to
                    move or destroy excitations. If bulk errors don't have this
                    property, decoding will fail when attempting to lift a solution
                    from the matcher requires dragging an excitation along a path but
                    there's no way to move the excitation along that path.
                4. Matchable-avoids-color. In parts of the dem that correspond to a
                    matchable code, at least one of the colors must be avoided.
                    Otherwise the matcher may be given a problem that can be solved
                    locally, but when lifting it needs to be solved non-locally.

        Returns:
            A decoder object that can be used to predict observable flips from
            detection event samples.

        Example:
            >>> import stim
            >>> import chromobius

            >>> dem = stim.Circuit('''
            ...     X_ERROR(0.1) 0 1 2 3 4 5 6 7
            ...     MPP Z0*Z1*Z2 Z1*Z2*Z3 Z2*Z3*Z4 Z3*Z4*Z5
            ...     DETECTOR(0, 0, 0, 1) rec[-4]
            ...     DETECTOR(1, 0, 0, 2) rec[-3]
            ...     DETECTOR(2, 0, 0, 0) rec[-2]
            ...     DETECTOR(3, 0, 0, 1) rec[-1]
            ...     M 0
            ...     OBSERVABLE_INCLUDE(0) rec[-1]
            ... ''').detector_error_model()

            >>> decoder = chromobius.CompiledDecoder.from_dem(dem)
        """
    @staticmethod
    def predict_obs_flips_from_dets_bit_packed(
        dets: np.ndarray,
    ) -> np.ndarray:
        """Predicts observable flips from detection events.

        Args:
            dets: A bit packed numpy array of detection event data. The array can either
                be 1-dimensional (a single shot to decode) or 2-dimensional (multiple
                shots to decode, with the first axis being the shot axis and the second
                axis being the detection event byte axis).

                The array's dtype must be np.uint8. If you have an array of dtype
                np.bool_, you have data that's not bit packed. You can pack it by
                using `np.packbits(array, bitorder='little')`. But ideally you
                should attempt to never have unpacked data in the first place,
                since it's 8x larger which can be a large performance loss. For
                example, stim's sampler methods all have a `bit_packed=True` argument
                that cause them to return bit packed data.

        Returns:
            A bit packed numpy array of observable flip data. The array will have
            the same number of dimensions as the dets argument.

            If dets is a 1D array, then the result has:
                shape = (math.ceil(num_obs / 8),)
                dtype = np.uint8
            If dets is a 2D array, then the result has:
                shape = (dets.shape[0], math.ceil(num_obs / 8),)
                dtype = np.uint8

            To determine if the observable with index k was flipped in shot s, compute:
                `bool((result[s, k // 8] >> (k % 8)) & 1)`

        Example:
            >>> import stim
            >>> import chromobius
            >>> import numpy as np

            >>> repetition_color_code = stim.Circuit('''
            ...     # Apply noise.
            ...     X_ERROR(0.1) 0 1 2 3 4 5 6 7
            ...     # Measure three-body stabilizers to catch errors.
            ...     MPP Z0*Z1*Z2 Z1*Z2*Z3 Z2*Z3*Z4 Z3*Z4*Z5 Z4*Z5*Z6 Z5*Z6*Z7
            ...
            ...     # Annotate detectors, with a coloring in the 4th coordinate.
            ...     DETECTOR(0, 0, 0, 2) rec[-6]
            ...     DETECTOR(1, 0, 0, 0) rec[-5]
            ...     DETECTOR(2, 0, 0, 1) rec[-4]
            ...     DETECTOR(3, 0, 0, 2) rec[-3]
            ...     DETECTOR(4, 0, 0, 0) rec[-2]
            ...     DETECTOR(5, 0, 0, 1) rec[-1]
            ...
            ...     # Check on the message.
            ...     M 0
            ...     OBSERVABLE_INCLUDE(0) rec[-1]
            ... ''')

            >>> # Sample the circuit.
            >>> shots = 4096
            >>> sampler = repetition_color_code.compile_detector_sampler()
            >>> dets, actual_obs_flips = sampler.sample(
            ...     shots=shots,
            ...     separate_observables=True,
            ...     bit_packed=True,
            ... )

            >>> # Decode with Chromobius.
            >>> dem = repetition_color_code.detector_error_model()
            >>> decoder = chromobius.compile_decoder_for_dem(dem)
            >>> predicted_flips = decoder.predict_obs_flips_from_dets_bit_packed(dets)

            >>> # Count mistakes.
            >>> differences = np.any(predicted_flips != actual_obs_flips, axis=1)
            >>> mistakes = np.count_nonzero(differences)
            >>> assert mistakes < shots / 5
        """
    @staticmethod
    def predict_weighted_obs_flips_from_dets_bit_packed(
        dets: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Predicts observable flips and weights from detection events.

        The returned weight comes directly from the underlying call to pymatching, not
        accounting for the lifting process.

        Args:
            dets: A bit packed numpy array of detection event data. The array can either
                be 1-dimensional (a single shot to decode) or 2-dimensional (multiple
                shots to decode, with the first axis being the shot axis and the second
                axis being the detection event byte axis).

                The array's dtype must be np.uint8. If you have an array of dtype
                np.bool_, you have data that's not bit packed. You can pack it by
                using `np.packbits(array, bitorder='little')`. But ideally you
                should attempt to never have unpacked data in the first place,
                since it's 8x larger which can be a large performance loss. For
                example, stim's sampler methods all have a `bit_packed=True` argument
                that cause them to return bit packed data.

        Returns:
            A tuple (obs, weights).
            Obs is a bit packed numpy array of observable flip data.
            Weights is a numpy array (or scalar) of floats.

            If dets is a 1D array, then the result has:
                obs.shape = (math.ceil(num_obs / 8),)
                obs.dtype = np.uint8
                weights.shape = ()
                weights.dtype = np.float32
            If dets is a 2D array, then the result has:
                shape = (dets.shape[0], math.ceil(num_obs / 8),)
                dtype = np.uint8
                weights.shape = (dets.shape[0],)
                weights.dtype = np.float32

            To determine if the observable with index k was flipped in shot s, compute:
                `bool((obs[s, k // 8] >> (k % 8)) & 1)`

        Example:
            >>> import stim
            >>> import chromobius
            >>> import numpy as np

            >>> repetition_color_code = stim.Circuit('''
            ...     # Apply noise.
            ...     X_ERROR(0.1) 0 1 2 3 4 5 6 7
            ...     # Measure three-body stabilizers to catch errors.
            ...     MPP Z0*Z1*Z2 Z1*Z2*Z3 Z2*Z3*Z4 Z3*Z4*Z5 Z4*Z5*Z6 Z5*Z6*Z7
            ...
            ...     # Annotate detectors, with a coloring in the 4th coordinate.
            ...     DETECTOR(0, 0, 0, 2) rec[-6]
            ...     DETECTOR(1, 0, 0, 0) rec[-5]
            ...     DETECTOR(2, 0, 0, 1) rec[-4]
            ...     DETECTOR(3, 0, 0, 2) rec[-3]
            ...     DETECTOR(4, 0, 0, 0) rec[-2]
            ...     DETECTOR(5, 0, 0, 1) rec[-1]
            ...
            ...     # Check on the message.
            ...     M 0
            ...     OBSERVABLE_INCLUDE(0) rec[-1]
            ... ''')

            >>> # Sample the circuit.
            >>> shots = 4096
            >>> sampler = repetition_color_code.compile_detector_sampler()
            >>> dets, actual_obs_flips = sampler.sample(
            ...     shots=shots,
            ...     separate_observables=True,
            ...     bit_packed=True,
            ... )

            >>> # Decode with Chromobius.
            >>> dem = repetition_color_code.detector_error_model()
            >>> decoder = chromobius.compile_decoder_for_dem(dem)
            >>> result = decoder.predict_weighted_obs_flips_from_dets_bit_packed(dets)
            >>> pred, weights = result
        """
def compile_decoder_for_dem(
    dem: stim.DetectorErrorModel,
) -> chromobius.CompiledDecoder:
    """Compiles a decoder for a stim detector error model.

    Args:
        dem: A stim detector error model. The detector error model must satisfy:
            1. Basis+Color annotations. Every detector that appears in an error
                must specify coordinate data including a fourth coordinate. The 4th
                coordinate indicates the basis and color of the detector with the
                convention:
                    0 = Red X
                    1 = Green X
                    2 = Blue X
                    3 = Red Z
                    4 = Green Z
                    5 = Blue Z
                    -1 = Ignore this Detector
            2. Rainbow triplets. Bulk errors with three symptoms in one basis should
                have one symptom of each color. Errors with three symptoms that
                repeat a color will cause an exception unless they can be decomposed
                into other basic errors.
            3. Movable excitations. It needs to be possible to combine bulk errors
                to form simpler errors with one or two symptoms that can be used to
                move or destroy excitations. If bulk errors don't have this
                property, decoding will fail when attempting to lift a solution
                from the matcher requires dragging an excitation along a path but
                there's no way to move the excitation along that path.
            4. Matchable-avoids-color. In parts of the dem that correspond to a
                matchable code, at least one of the colors must be avoided.
                Otherwise the matcher may be given a problem that can be solved
                locally, but when lifting it needs to be solved non-locally.

    Returns:
        A decoder object that can be used to predict observable flips from
        detection event samples.

    Example:
        >>> import stim
        >>> import chromobius

        >>> dem = stim.Circuit('''
        ...     X_ERROR(0.1) 0 1 2 3 4 5 6 7
        ...     MPP Z0*Z1*Z2 Z1*Z2*Z3 Z2*Z3*Z4 Z3*Z4*Z5
        ...     DETECTOR(0, 0, 0, 1) rec[-4]
        ...     DETECTOR(1, 0, 0, 2) rec[-3]
        ...     DETECTOR(2, 0, 0, 0) rec[-2]
        ...     DETECTOR(3, 0, 0, 1) rec[-1]
        ...     M 0
        ...     OBSERVABLE_INCLUDE(0) rec[-1]
        ... ''').detector_error_model()

        >>> decoder = chromobius.compile_decoder_for_dem(dem)
    """
def sinter_decoders() -> dict[str, sinter.Decoder]:
    """A dictionary describing chromobius to sinter.

    Giving the result of this function to the `custom_decoders` argument of
    `sinter.collect` will tell sinter about the decoder 'chromobius'. On the
    command line, the equivalent argument is
    `--custom_decoders 'chromobius:sinter_decoders'`.

    Returns:
        The dict `{'chromobius': <an object compatible with sinter.Decoder>}`.
    """
