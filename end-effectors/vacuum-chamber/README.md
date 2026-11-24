# vacuum-chamber

Dancefloor lid and vacuum valve. The valve is `M8` / `M9` on the gantry port. There is no second port. On and off delays are 5 s.

Close waypoints, robot frame: (−3, 0, 0) then (−3, −27, 0). Loading position: (−118, 0, 0). Evacuation is refused unless the chamber is marked closed. Motion is refused while it is marked closed. Homing vents first when the chamber is not marked vented.

The loading position is outside gantry 006's X limit of −116. `loading_position` raises against that frame. The pescador2 config uses X low −119. The edge contract carries that question.
