# Room measurements

From this folder, run:

```powershell
python -m pip install -r requirements.txt
python measure.py
```

Python's standard Tkinter provides the small window; Pillow loads the image.

1. Click two endpoints on the image.
2. For a known distance, type `10'11''` (10 feet 11 inches), `24''` (24 inches), or `10.2m`, then press Enter.
3. Select another pair. Its estimated distance appears above the image immediately. Leave the input empty and press Enter to keep that estimate in the list.

Every known distance contributes equally to the average **meters per original image pixel**. Known lines and list entries show their percentage difference from that average: green within 5%, orange within 10%, red above 10%. Blue lines are estimates and update whenever the average changes. The line numbers match the list. Both meters and feet/inches are displayed.

Use the mouse wheel to zoom, **Shift + left-drag** or right-drag to pan, and **Fit image** to reset the view. Press Escape to cancel a selection; **Ctrl+Z** or **Undo** removes only the last pending endpoint, or the last saved measurement if no endpoints are pending; **Clear all** resets the session. Nothing is saved automatically when you close the app.

Press **Ctrl+P** or **Save image** to save an annotated PNG in `room/`. Each saved line is labeled with its distance in meters only and its scale difference (or “estimate”). Exports use the original image resolution and include the entire image regardless of zoom or pan. Only saved measurements are included; press Enter first to keep a pending measurement. Filenames such as `room_pic_annotated_20261017_153000_123456.png` keep the source and previous exports intact. The saved image is a snapshot, not a session you can reload for editing.

Replace `room_pic.png` to use a different plan, or run `python measure.py another_image.jpg`. The default image is always loaded from beside the script; a supplied relative path is relative to your terminal's current folder.

Colors measure agreement between the entered scales, not absolute accuracy. One calibration always agrees with itself. A distorted plan or perspective photo may have different scales in different regions or directions; a single average cannot correct that. Choose long, clearly defined reference distances for better accuracy.

Choose **Free**, **Horizontal**, or **Vertical** at the top right before drawing. Horizontal locks the second endpoint to the first endpoint's height; Vertical locks it to the same horizontal position. The chosen mode stays active for subsequent lines.
