"""Entry point: `python app.py` launches CareerPath Guide at http://127.0.0.1:7860.

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from careerpath.ui import build_ui

if __name__ == "__main__":
    build_ui().launch()
