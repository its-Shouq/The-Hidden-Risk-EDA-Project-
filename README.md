# THE HIDDEN RISK — Final Submission

## Run locally

1. Extract this ZIP and open the **THE_HIDDEN_RISK_FINAL_FIXED** folder in VS Code.
2. Open the terminal in this folder:

   ```powershell
   pip install -r requirements.txt
   python -m streamlit run app.py --server.port 8505
   ```

3. Open **http://localhost:8505**. This separate port avoids mixing it up with older versions.

Or on Windows, double-click `RUN_DASHBOARD.bat` in the project folder.

## Final adjustments

- The original **white airliner** illustration and the existing dashboard theme remain unchanged.
- The species selector lists **at most 12 frequently recorded, compatible species** for the selected phase, animal size and single/multiple selection. These are actual FAA `SPECIES` values.
- Heatmap clicks select an observed species for the clicked phase and size. Every heatmap cell with a compatible identified species has been tested. The one empty cell (Taxi × Large × Multiple) displays `N/A` instead of an inert button.
- Ground mammals and reptiles are only selectable in ground flight phases.
- All rates use exact reported damage counts divided by reported strike counts. The heatmap rate aggregates **all** species in a phase/size/strike group, while the simulator rate additionally filters to the **selected species**, so the two rates can differ.
- Small samples (fewer than 10 matching reports) are marked in the simulator status.
- Damage animations represent illustrative outcomes; the cleaned data do not establish damaged aircraft parts for each specific scenario.
- No file-upload/download buttons are part of the dashboard.
