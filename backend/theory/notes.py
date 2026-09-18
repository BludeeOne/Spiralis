# Notes.py 
# Author: Erik Flores-Siemsen
# Date: 9-17-2002
# Description: A foundational file for the rest of the program. All notes declerations

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
    return Notes[pitch % 12]

