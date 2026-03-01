Ultron

Ultron is a real-time hand-gesture interaction project built in Python using MediaPipe and a live webcam feed.
It explores how continuous hand motion can be translated into smooth control signals for manipulating digital objects, similar to interaction models used in AR and XR systems.

Project Goal

The goal of Ultron is to treat the human hand as a continuous input device, not just a source of discrete gestures.

Instead of answering “is a gesture detected?”, Ultron focuses on:

How hand motion changes over time

How those changes can be mapped to stable control values

How to use those values to drive interactive visuals

Features
Implemented

Real-time webcam hand tracking

Multi-hand detection with handedness

21-point landmark extraction per hand

Pinch detection (true / false)

Pinch distance measurement

In Progress

Signal normalization

Motion smoothing

Gesture-gated control values

Planned

Visual object scaling and manipulation

Two-hand interactions (scale + rotate)

3D rendering layer

Hand calibration support

Tech Stack

Python

OpenCV

MediaPipe Tasks API (Hand Landmarker)

NumPy

How It Works

Capture frames from a live webcam feed

Detect hand landmarks using MediaPipe

Compute distances between relevant landmarks

Normalize and smooth raw motion data

Use control values to manipulate visual elements
