"""Render pydoctor data as HTML."""

DOCTYPE:bytes = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''
import os

from typing import List

from pydoctor.templatewriter.writer import TemplateWriter
TemplateWriter = TemplateWriter

__all__ = ['TemplateWriter', 'IWriter']

