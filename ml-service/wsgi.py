# ====================================================================
# wsgi.py  —  Production WSGI entrypoint for the NeuroTunes ML server
# --------------------------------------------------------------------
# Gunicorn (already listed in requirements.txt) imports `app` from this
# module:   gunicorn -c gunicorn.conf.py wsgi:app
#
# Importing app.py runs its one-time startup side effects at module level
# (MusicGenerator load, whisper model load, output/ + logs/ dir creation).
# The production config runs a SINGLE worker (see gunicorn.conf.py) so the
# heavy whisper/torch models are loaded once and any in-process state stays
# consistent — exactly as under the old `flask run` dev server. Federation
# now runs as a separate microservice, so no coordinator thread lives here.
# ====================================================================

from app import app

if __name__ == "__main__":
    # Fallback for `python wsgi.py` (development only). Production uses gunicorn.
    import os
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
