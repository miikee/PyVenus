import json
import numpy as np
import pandas as pd
from uuid import uuid4
from typing import Union
from . import Connection


class Variable:
    """Replicates functionality of basic Venus variables (i.e. string, integer, float) in python
    """    
    def __init__(self, con: Connection, value: Union[int,float,str] = 0, name: str = None):
        """Initialize a new variable

        None as value for the name parameter (default) will generate a unique ID for this variable in the Venus environment.
        By setting a name explicitly the generated HSL code is easier to read/debug.

        Args:
            con (Connection): Connection object to Venus environment
            value (Union[int, float, str], optional): Starting value for variable. Defaults to 0.
            name (str, optional): Name the variable should carry in Venus environment. Defaults to None which will generate a random name.
        """        
        self.__con = con
        self.value = value

        if type(value) not in [int, str, float]:
            raise Exception("Only values of type int, str, or float are accepted")

        if name is None:
            name = "variable_" + str(uuid4()).replace("-","")
        self.__name = name

        if isinstance(self.value, str):
            value_string = f"\"{self.value}\""
        else:
            value_string = str(self.value)

        self.__con.execute(definitions=f'variable {self.name} ({value_string});')

    def __str__(self):
        return str(self.value)

    @property
    def name(self):
        return self.__name

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    def push(self):
        """Push the current state of the variable to the Venus environment
        """        
        value_string = f'"{self.value}"' if isinstance(self.value, str) else str(self.value)
        self.__con.execute(f"{self.__name} = {value_string};")

    def pull(self):
        """Pull the current state of the variable from the Venus environment
        """        
        ret = self.__con.execute(f'addJSON_variable(___JSON___, {self.__name}, "{self.__name}");')
        ret = json.loads(ret)
        self.value = ret[self.__name]


class Array(list):
    """Replicates functionality of Venus arrays in python. Expands basic list type from python.
    """
    def __init__(self, con: Connection, value: list = None, name: str = None):
        """Intialize a new array

        None as value for the name parameter (default) will generate a unique ID for this array in the Venus environment.
        By setting a name explicitly the generated HSL code is easier to read/debug.

        Args:
            con (Connection): Connection object to Venus environment
            value (list, optional): Starting value of the array in the form of a python list. Defaults to None which generates an empty array.
            name (str, optional): Name the array should carry in the Venus environment. Defaults to None which will generate a random name.
        """        
        
        list.__init__([])
        if value is None:
            value = []
        self.extend(value)
        self.__con = con

        if name is None:
            name = "array_" + str(uuid4()).replace("-","")
        self.__name = name

        self.__con.execute(definitions=f'variable {self.__name}[];')
        self.push()

    @property
    def name(self):
        return self.__name

    def push(self):
        """Push current state of the array to the Venus environment
        """        
        code = f"{self.__name}.SetSize(0);\n"
        for item in self.copy():
            value_string = f'"{item}"' if isinstance(item, str) else str(item)
            code += f"{self.__name}.AddAsLast({value_string});\n"
        self.__con.execute(code)

    def pull(self):
        """Pull current state of the array from the Venus environment
        """        
        ret = self.__con.execute(f'addJSON_array(___JSON___, {self.__name}, "{self.__name}");')
        ret = json.loads(ret)
        self.clear()
        self.extend(ret[self.__name])


class Sequence:
    """Replicates functionality of a Venus sequence in python
    """    
    def __init__(self, con: Connection, name: str = None, copy: Union['Sequence', str] = None, deck_sequence: bool = False):
        """Initialize a new sequence 

        None as value for the name parameter (default) will generate a unique ID for this sequence in the Venus environment.
        By setting a name explicitly the generated HSL code is easier to read/debug.
        If deck_sequence is set to True (and copy is None) the sequence is not initiated in the Venus environment (i.e. it already exists)
        For deck sequences the name parameter is required!

        Args:
            con (Connection): Connection object to Venus environment
            name (str, optional): Name the sequence should carry in Venus environment. Defaults to None which will generate a random name.
            copy (Union[Sequence, str], optional): Either an existing Sequence object or a string referencing an existing Venus sequence (e.g. deck sequence), the content of which will be copied. Defaults to None which generates an empty sequence.
            deck_sequence (bool, optional): Is this a reference to a deck sequence?
        """        
        self.__con = con
        self.__current = 0
        self.__end = 0    

        if name is None:
            name = "sequence_" + str(uuid4()).replace("-","")
            if deck_sequence:
                raise Exception("For deck sequences the name parameter is required (i.e. name of the sequence on the deck layout)")

        self.__name = name

        if isinstance(copy, Sequence):
            do_pull = True
            seq_name = copy.name
        elif copy is not None:
            do_pull = True
            seq_name = copy
        else:
            do_pull = False
            seq_name = None

        if do_pull:
            ret = self.__con.execute(f'addJSON_sequence(___JSON___, {seq_name}, "{seq_name}");')
            ret = json.loads(ret)
            self.__df = pd.DataFrame(
                {
                    'labware': ret[seq_name]["labware"],
                    'position': ret[seq_name]["position"]
                }
            )
            self.end = ret[seq_name]["end"]
            self.current = ret[seq_name]["current"]
        else:
            self.__df = pd.DataFrame(
                {
                    'labware': [],
                    'position': []
                }
            )
            self.end = 0
            self.current = 0

        if deck_sequence:
            self.pull()
        else:
            self.__con.execute(definitions=f'sequence {self.__name};')
            self.push()

    def __str__(self):
        return f"Current: {self.current}\n" \
            f"End: {self.end}\n" \
            f"{self.__df.__str__()}"

    @property
    def name(self):
        return self.__name

    @property
    def current(self):
        return self.__current

    @current.setter
    def current(self, current):
        self.set_current(current)

    @property
    def end(self):
        return self.__end

    @end.setter
    def end(self, end):
        self.set_end(end)

    @property
    def remaining(self):
        if self.current > 0:
            return self.end - (self.current - 1)
        else:
            return 0

    @property
    def total(self):
        return len(self.__df.index)

    def set_current(self, current: int) -> "Sequence":
        if current > self.end or current < 0:
            current = 0
        self.__current = current

        return self

    def set_end(self, end: int) -> "Sequence":
        if end < 0:
            end = 0
        if end > self.total:
            end = self.total
        self.__end = end

        self.set_current(self.current)

        return self

    def from_list(self, labware: list, positions: list) -> "Sequence":
        """Update the content of the sequence to the give lists of labware and positions

        If the two lists do not have the same length then the shorter one is recycled to the full length.

        Returns the updated sequence

        Args:
            labware (list): List of Venus labware IDs
            positions (list): List of position IDs on the specified labware IDs
        """        
        length = max(len(labware), len(positions))

        self.__df = pd.DataFrame(
            {
                'labware': np.resize(labware, length),
                'position': np.resize(positions, length)
            }
        )
        self.set_end(length)
        self.set_current(1)

        return self

    """     def from_dataframe(self, dataframe: pd.DataFrame) -> "Sequence":
        pass """

    def push(self):
        """Push the current state of the sequence to the Venus environment
        """        
        code = f'{{ sequence __temp; {self.__name} = __temp; }}\n'
        for row in self.__df.itertuples():
            code += f'{self.__name}.Add("{row.labware}", "{row.position}");\n'
        code += f'{self.__name}.SetCount({self.end});\n'
        code += f'{self.__name}.SetCurrentPosition({self.current});\n'
        self.__con.execute(code)

    def pull(self):
        """Pull the current state of the sequence to the Venus environment
        """        
        ret = self.__con.execute(f'addJSON_sequence(___JSON___, {self.__name}, "{self.__name}");')
        ret = json.loads(ret)
        self.__df = pd.DataFrame(
            {
                'labware': ret[self.__name]["labware"],
                'position': ret[self.__name]["position"]
            }
        )
        self.set_end(ret[self.__name]["end"])
        self.set_current(ret[self.__name]["current"])

    def add(self, labware: str, position: str, at_index: int = None) -> "Sequence":
        """Add a new item (defined by labware ID and position) to the sequence

        If the ad_index parameter is omitted the new item is appended at the end.

        Args:
            labware (str): Venus labware ID
            position (str): Position on the labware
            at_index (int, optional): One-based position index where the item should be added. Defaults to None which will append to the end.
        """    

        old_total = self.total
        
        if at_index is None:
            self.__df = self.__df.append(
                pd.DataFrame(
                    {
                        "labware": [labware] if isinstance(labware, str) else labware,
                        "position": [position] if isinstance(position, str) else position,
                    }
                ),
                ignore_index=True
            )
        else:
            self.__df = pd.concat([
                self.__df.iloc[:at_index-2],
                pd.DataFrame(
                    {
                        "labware": [labware] if isinstance(labware, str) else labware,
                        "position": [position] if isinstance(position, str) else position,
                    }
                ),
                self.__df.iloc[at_index-1:]
            ],
            ignore_index=True)

        # if the end position of the sequence as on the last position before then also set the end position on the last position for the updated sequence
        if self.end == old_total:
            self.set_end(self.total)

        # adding elements to a sequence resets the current position (always annoyed me in Venus that I have to do this explicitly)
        if self.current == 0:
            self.set_current(1)

        return self

    def remove(self, at_index: int) -> "Sequence":
        """Remove an item from the sequence at the specified index (one-based)

        Args:
            at_index (int): One-based index of the position to remove
        """

        if isinstance(at_index, int):
            # remove a single row with the specified index
            self.__df.drop([at_index-1], inplace=True).reset_index(inplace=True)
        else:
            # remove multiple list from list of indexes
            self.__df.drop([x - 1 for x in at_index], inplace=True).reset_index(inplace=True)

        # make sure current and end position are meaningful (the setting functions will take care of this)
        self.set_end(self.end)
        self.set_current(self.current)

        return self



    def clear(self) -> "Sequence":
        """Remove all items from a sequence
        """        

        self.__df = self.__df.iloc[0:0]
        self.set_current(0)
        self.set_end(0)

        return self


class Device:
    """Replicate the functionality of a Venus device object in python
    """    

    def __init__(self, con: Connection, layout_file: str, name: str = "ML_STAR", main: bool = True):
        """Initialize the device object

        Args:
            con (Connection): Connection object to Venus environment
            layout_file (str): Path to Venus deck layout file
            name (str, optional): Name of the device in Venus (e.g. ML_STAR, HxFan). Defaults to "ML_STAR".
            main (bool, optional): Is this the main device object (e.g. ML_STAR). Set to False for e.g. HxFan. Defaults to True.
        """        

        self.__con = con
        self.__name = name
        self.__con.execute(definitions=f'device {name}("{layout_file}", "{name}", hslTrue);')

        if main:
            self.__con.execute(f"__DEVICE__ = {name};")

    @property
    def name(self):
        return self.__name

class Liquidclass:
    """Python class representing a Venus liquid class
    """    
    def __init__(self, name: str):
        """Initialize the liquid class

        Args:
            name (_type_): Name of the liquid class in the liquid class database
        """        
        self.__name = name
    
    @property
    def name(self):
        return self.__name

    def __str__(self):
        return self.name
