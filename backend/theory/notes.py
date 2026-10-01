# Notes.py 
# Author: Erik Flores-Siemsen
# Creation Date: 9-17-2026
# Description: A foundational file for the rest of the program. 
# All notes declerations

from dataclasses import dataclass

@dataclass(frozen=True)
class Note:
    pitch: int
    sharp_name: str
    flat_name: str

NOTES: list[Note] = [
    Note(0, "C", "C"),   
    Note(1, "C#", "Db"),
    Note(2, "D", "D"),   
    Note(3, "D#", "Eb"),
    Note(4, "E", "E"),
    Note(5, "F", "F"),   
    Note(6, "F#", "Gb"),
    Note(7, "G", "G"),   
    Note(8, "G#", "Ab"),
    Note(9, "A", "A"),   
    Note(10, "A#", "Bb"),
    Note(11, "B", "B"),
]

def note_at(pitch: int) -> Note:
    return NOTES[pitch % 12]

def pitch_of(name: str) -> Note:
    return 

"""useful table to reference
Note	Frequency (Hz)
A	    440.00
A#	    466.16
B	    493.88
C	    523.25
C#	    554.37
D	    587.33
D#	    622.25
E	    659.26
F	    698.46
F#	    739.99
G	    783.99
G#	    830.61

each note being approximately 1.0595 times the frequency of the previous note."""