#!/usr/bin/env python
"""
Main application entry point for Auto AI Agents Creator.
This module launches the Gradio web interface.
"""
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from main.gradio_app import create_interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch()
