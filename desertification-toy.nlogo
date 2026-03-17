globals [
  vegetation-count
  degraded-count
  desert-count
]

patches-own [
  state
  water
]

to setup
  clear-all
  ask patches [
    set water random-float 1.0
    ifelse water > 0.4
      [ set state "vegetated"  set pcolor green ]
      [ ifelse water > 0.2
        [ set state "degraded"  set pcolor yellow ]
        [ set state "desert"    set pcolor red ] ]
  ]
  reset-ticks
end

to go
  if ticks >= max-ticks [ stop ]
  rain
  graze
  spread-desertification
  recover
  update-counts
  tick
end

to rain
  ask patches [
    set water water + rainfall-rate * random-float 1.0
    if water > 1.0 [ set water 1.0 ]
  ]
end

to graze
  ask patches with [ state = "vegetated" ] [
    set water water - grazing-pressure
    if water < 0 [ set water 0 ]
    if water < 0.3 [
      set state "degraded"
      set pcolor yellow
    ]
  ]
end

to spread-desertification
  ask patches with [ state = "desert" ] [
    ask neighbors with [ state = "degraded" ] [
      if random-float 1.0 < spread-rate [
        set state "desert"
        set pcolor red
        set water 0
      ]
    ]
  ]
end

to recover
  ask patches with [ state = "degraded" ] [
    set water water + rainfall-rate * 0.5
    if water > 0.5 [
      set state "vegetated"
      set pcolor green
    ]
    if water < 0.1 [
      set state "desert"
      set pcolor red
    ]
  ]
end

to update-counts
  set vegetation-count count patches with [ state = "vegetated" ]
  set degraded-count   count patches with [ state = "degraded" ]
  set desert-count     count patches with [ state = "desert" ]
end
@#$#@#$#@
GRAPHICS-WINDOW
210
10
648
449
-1
-1
13.0
1
10
1
1
1
0
1
1
1
-16
16
-16
16
0
0
1
ticks
30.0

SLIDER
10
55
182
88
rainfall-rate
rainfall-rate
0
0.1
0.03
0.001
1
NIL
HORIZONTAL

SLIDER
10
95
182
128
grazing-pressure
grazing-pressure
0
0.1
0.04
0.001
1
NIL
HORIZONTAL

SLIDER
10
135
182
168
spread-rate
spread-rate
0
0.5
0.1
0.01
1
NIL
HORIZONTAL

SLIDER
10
175
182
208
max-ticks
max-ticks
10
500
100.0
10
1
NIL
HORIZONTAL

BUTTON
10
10
73
43
NIL
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
80
10
143
43
NIL
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
0

MONITOR
10
215
112
260
vegetation
vegetation-count
0
1
11

MONITOR
10
265
112
310
degraded
degraded-count
0
1
11

MONITOR
10
315
112
360
desert
desert-count
0
1
11

@#$#@#$#@
## WHAT IS IT?

A minimal desertification model. Patches are vegetated, degraded, or desert.
Rainfall restores land; grazing degrades it; desertification spreads to neighbors.

## PARAMETERS

- **rainfall-rate**: Water added per tick
- **grazing-pressure**: Water removed per tick by livestock
- **spread-rate**: Probability desert spreads to degraded neighbors
- **max-ticks**: Simulation length
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

@#$#@#$#@
NetLogo 6.4.0
@#$#@#$#@
setup
repeat 100 [ go ]
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
