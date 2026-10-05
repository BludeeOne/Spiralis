# Spiralis
A website/app that is a one-stop shop for aspiring musicians and accomplished song-writers alike. It can listen to live audio, parse through songs, or take a simple written input in order to suggest and show the user every possible correct note/chord that is within key. 

backend/
  app/main.py           FastAPI routes 
  app/schemas.py        request/response contracts
  app/audio/features.py Essentia: decode -> chroma -> beats -> pitch-class sets
 
 pip install -r requirements.txt
pytest -q

backend/app
backend/app/audio
backend/app/routes

backend/theory
