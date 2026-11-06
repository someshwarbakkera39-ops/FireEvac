@echo off
echo =======================================================================
echo  Smart Emergency Evacuation Planning & Digital Twin System (Block A)
echo =======================================================================
echo.
echo Starting Flask Digital Twin Server on http://localhost:5000 ...
echo Opening Master Demonstration Hub in your default browser...
start "" "http://localhost:5000"
python app.py
pause

