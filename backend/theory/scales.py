# scales.py 
# Author: Erik Flores-Siemsen
# Date: September 2026
# Description: Every scale on guitar listed out and available to view
# Instead of writing out each scale, write an algorithm that finds the scale depending on the key

from .notes import NOTES

# whole\half step pattern for each scale type
Scale_Intervals = {
    "major":            [2, 2, 1, 2, 2, 2, 1],
    "natural_minor":    [2, 1, 2, 2, 1, 2, 2],
    "melodic_minor":    [2, 1, 2, 2, 2, 2, 1],
    "dorian":           [2, 1, 2, 2, 2, 1, 2],
    "mixolydian":       [2, 2, 1, 2, 2, 1, 2],
}

def get_scale(root:str, scale_type: str = )