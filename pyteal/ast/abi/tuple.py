from typing import (
    List,
    Sequence,
    Optional,
    cast,
)

from ...types import TealType
from ..expr import Expr
from ..seq import Seq
from ..int import Int
from ..unaryexpr import Len
from ..binaryexpr import ExtractUint16
from ..naryexpr import Concat
from ..substring import Extract, Substring, Suffix
from ..scratchvar import ScratchVar

from .type import Type, ComputedType
from .bool import (
    Bool,
    consecutiveBools,
    boolSequenceLength,
    encodeBoolSequence,
    boolAwareStaticByteLength,
)
from .uint import NUM_BITS_IN_BYTE, Uint16


def encodeTuple(values: Sequence[Type]) -> Expr:
    heads: List[Optional[Expr]] = []
    head_length_static: int = 0

    ignoreNext = 0
    for i, elem in enumerate(values):
        if ignoreNext > 0:
            ignoreNext -= 1
            continue

        if type(elem) is Bool:
            numBools = consecutiveBools(values, i)
            ignoreNext = numBools - 1
            head_length_static += boolSequenceLength(numBools)
            heads.append(
                encodeBoolSequence(cast(Sequence[Bool], values[i : i + numBools]))
            )
            continue

        if elem.is_dynamic():
            head_length_static += 2
            heads.append(None)  # a placeholder
            continue

        head_length_static += elem.byte_length_static()
        heads.append(elem.encode())

    tail_offset = Uint16()
    tail_offset_accumulator = Uint16()
    tail_holder = ScratchVar(TealType.bytes)
    encoded_tail = ScratchVar(TealType.bytes)

    firstDynamicTail = True
    for i, elem in enumerate(values):
        if elem.is_dynamic():
            if firstDynamicTail:
                firstDynamicTail = False
                updateVars = Seq(
                    tail_holder.store(encoded_tail.load()),
                    tail_offset.set(head_length_static)
                )
            else:
                updateVars = Seq(
                    tail_holder.store(Concat(tail_holder.load(), encoded_tail.load())),
                    tail_offset.set(tail_offset_accumulator.get())
                )
            
            notLastDynamicValue = any([nextValue.is_dynamic() for nextValue in values[i+1:]])
            if notLastDynamicValue:
                updateAccumulator = tail_offset_accumulator.set(tail_offset.get() + Len(encoded_tail.load()))
            else:
                updateAccumulator = Seq()

            heads[i] = Seq(
                encoded_tail.store(elem.encode()),
                updateVars,
                updateAccumulator,
                tail_offset.encode(),
            )
    
    toConcat = cast(List[Expr], heads)
    if not firstDynamicTail:
        toConcat.append(tail_holder.load())

    return Concat(*toConcat)


def indexTuple(
    valueTypes: Sequence[Type], encoded: Expr, index: int, output: Type
) -> Expr:
    if not (0 <= index < len(valueTypes)):
        raise ValueError("Index outside of range")

    offset = 0
    ignoreNext = 0
    lastBoolStart = 0
    lastBoolLength = 0
    for i, typeBefore in enumerate(valueTypes[:index]):
        if ignoreNext > 0:
            ignoreNext -= 1
            continue

        if type(typeBefore) is Bool:
            lastBoolStart = offset
            lastBoolLength = consecutiveBools(valueTypes, i)
            offset += boolSequenceLength(lastBoolLength)
            ignoreNext = lastBoolLength - 1
            continue

        if typeBefore.is_dynamic():
            offset += 2
            continue

        offset += typeBefore.byte_length_static()

    valueType = valueTypes[index]
    if not valueType.has_same_type_as(output):
        raise TypeError("Output type does not match value type")

    if ignoreNext > 0:
        # value is part of a bool sequence
        assert type(output) is Bool
        bitOffsetInBoolSeq = lastBoolLength - ignoreNext
        bitOffsetInEncoded = lastBoolStart * NUM_BITS_IN_BYTE + bitOffsetInBoolSeq
        return output.decodeBit(encoded, Int(bitOffsetInEncoded))

    if valueType.is_dynamic():
        startIndex = ExtractUint16(encoded, Int(offset))
        if index + 1 == len(valueTypes):
            return output.decode(encoded, startIndex=startIndex)

        endIndex = ExtractUint16(encoded, Int(offset + 2))
        return output.decode(encoded, startIndex=startIndex, endIndex=endIndex)

    startIndex = Int(offset)
    length = Int(valueType.byte_length_static())
    return output.decode(encoded, startIndex=startIndex, length=length)


class Tuple(Type):
    def __init__(self, *valueTypes: Type) -> None:
        super().__init__(TealType.bytes)
        self.valueTypes = list(valueTypes)

    def has_same_type_as(self, other: Type) -> bool:
        return (
            type(other) is Tuple
            and len(self.valueTypes) == len(other.valueTypes)
            and all(
                self.valueTypes[i].has_same_type_as(other.valueTypes[i])
                for i in range(len(self.valueTypes))
            )
        )

    def new_instance(self) -> "Tuple":
        return Tuple(*self.valueTypes)

    def is_dynamic(self) -> bool:
        return any(valueType.is_dynamic() for valueType in self.valueTypes)

    def byte_length_static(self) -> int:
        if self.is_dynamic():
            raise ValueError("Type is dynamic")
        return boolAwareStaticByteLength(self.valueTypes)

    def decode(
        self,
        encoded: Expr,
        *,
        startIndex: Expr = None,
        endIndex: Expr = None,
        length: Expr = None
    ) -> Expr:
        if startIndex is None:
            assert length is None
            assert endIndex is None
            extracted = encoded
        elif length is not None:
            assert endIndex is None
            extracted = Extract(encoded, startIndex, length)
        elif endIndex is not None:
            extracted = Substring(encoded, startIndex, endIndex)
        else:
            extracted = Suffix(encoded, startIndex)
        return self.stored_value.store(extracted)

    def set(self, *values: Type) -> Expr:
        if len(self.valueTypes) != len(values):
            raise ValueError(
                "Incorrect length for values. Expected {}, got {}".format(
                    len(self.valueTypes), len(values)
                )
            )
        if not all(
            self.valueTypes[i].has_same_type_as(values[i])
            for i in range(len(self.valueTypes))
        ):
            raise ValueError(
                "Input values do not match type"
            )  # TODO: add more to error message
        return self.stored_value.store(encodeTuple(values))

    def encode(self) -> Expr:
        return self.stored_value.load()

    def length_static(self) -> int:
        return len(self.valueTypes)

    def length(self) -> Expr:
        return Int(self.length_static())

    def __getitem__(self, index: int) -> "TupleElement":
        return TupleElement(self, index)

    def __str__(self) -> str:
        return "({})".format(",".join(map(lambda x: x.__str__(), self.valueTypes)))


Tuple.__module__ = "pyteal"


class TupleElement(ComputedType[Type]):
    def __init__(self, tuple: Tuple, index: int) -> None:
        super().__init__(tuple.valueTypes[index])
        self.tuple = tuple
        self.index = index

    def store_into(self, output: Type) -> Expr:
        return indexTuple(
            self.tuple.valueTypes, self.tuple.encode(), self.index, output
        )


TupleElement.__module__ = "pyteal"
