# Keyframe Animation

## Overview

Keyframes mark specific points in time where a property has a defined value. After Effects interpolates between keyframes to create smooth animations. Scripts can create, modify, and manipulate keyframes programmatically.

## Keyframe Basics

### Adding Keyframes

```javascript
var position = layer.property("Position");
var opacity = layer.property("Opacity");

// Add keyframe by setting value at time
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(2, [1920, 540]);

// Add keyframe explicitly
position.addKey(1);
position.setValueAtTime(1, [960, 540]);

// Add keyframe with value
opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(0.5, 100);
opacity.setValueAtTime(1, 0);
```

### Removing Keyframes

```javascript
var prop = layer.property("Position");

// Remove specific keyframe by index (1-based)
prop.removeKey(1);  // Remove first keyframe

// Remove all keyframes
function removeAllKeys(prop) {
    while (prop.numKeys > 0) {
        prop.removeKey(1);
    }
}

// Remove keyframes in range
function removeKeysInRange(prop, startTime, endTime) {
    for (var i = prop.numKeys; i >= 1; i--) {
        var keyTime = prop.keyTime(i);
        if (keyTime >= startTime && keyTime <= endTime) {
            prop.removeKey(i);
        }
    }
}

// Usage
removeKeysInRange(layer.property("Position"), 1, 2);
```

### Accessing Keyframes

```javascript
var prop = layer.property("Position");

// Get number of keyframes
var numKeys = prop.numKeys;

// Get keyframe time
var time = prop.keyTime(1);  // Time of first keyframe

// Get keyframe value
var value = prop.keyValue(1);  // Value of first keyframe

// Get all keyframes
for (var i = 1; i <= prop.numKeys; i++) {
    var t = prop.keyTime(i);
    var v = prop.keyValue(i);
    $.writeln("Key " + i + " at " + t + ": " + v);
}
```

### Finding Keyframes

```javascript
var prop = layer.property("Position");

// Find nearest keyframe to time
var nearestIndex = prop.nearestKeyIndex(1.5);

// Get keyframe before time
function getKeyBefore(prop, time) {
    for (var i = prop.numKeys; i >= 1; i--) {
        if (prop.keyTime(i) < time) {
            return i;
        }
    }
    return 0;  // No keyframe before
}

// Get keyframe after time
function getKeyAfter(prop, time) {
    for (var i = 1; i <= prop.numKeys; i++) {
        if (prop.keyTime(i) > time) {
            return i;
        }
    }
    return 0;  // No keyframe after
}

// Usage
var beforeIndex = getKeyBefore(prop, 1.5);
var afterIndex = getKeyAfter(prop, 1.5);
```

## Keyframe Interpolation

### Temporal Interpolation

```javascript
var prop = layer.property("Position");

// Set keyframes
prop.setValueAtTime(0, [0, 540]);
prop.setValueAtTime(2, [1920, 540]);

// Set temporal interpolation type
prop.setTemporalInterpolationAtKey(1, KeyframeInterpolationType.LINEAR);
prop.setTemporalInterpolationAtKey(2, KeyframeInterpolationType.BEZIER);

// Options:
// KeyframeInterpolationType.LINEAR - Straight line between keyframes
// KeyframeInterpolationType.BEZIER - Smooth Bezier curve
// KeyframeInterpolationType.HOLD - Stepped (no interpolation)
```

### Spatial Interpolation

```javascript
var prop = layer.property("Position");

// Set spatial interpolation (for multi-dimensional properties)
prop.setSpatialInterpolationAtKey(1, KeyframeSpatialInterpolationType.LINEAR);
prop.setSpatialInterpolationAtKey(2, KeyframeSpatialInterpolationType.BEZIER);

// Options:
// KeyframeSpatialInterpolationType.LINEAR - Straight path
// KeyframeSpatialInterpolationType.BEZIER - Curved path
// KeyframeSpatialInterpolationType.AUTO_BEZIER - Automatic smooth curve
// KeyframeSpatialInterpolationType.CLAMPED - Smooth with straight ends
```

### Keyframe Ease

```javascript
var prop = layer.property("Position");

// Create KeyframeEase objects
var easeIn = new KeyframeEase(0.33, 50);   // influence, speed
var easeOut = new KeyframeEase(0.33, 50);

// Set ease at keyframe
prop.setTemporalEaseAtKey(1, [easeIn], [easeOut]);

// Get ease at keyframe
var inEases = prop.getTemporalEaseAtKey(1);
var outEases = prop.getTemporalEaseAtKey(1);

var inEase = inEases[0];
var outEase = outEases[0];

$.writeln("In influence: " + inEase.influence);
$.writeln("Out influence: " + outEase.influence);
$.writeln("In speed: " + inEase.speed);
$.writeln("Out speed: " + outEase.speed);
```

### Keyframe Velocity

```javascript
var prop = layer.property("Position");

// Set velocity at keyframe (pixels per second)
prop.setVelocityAtKey(1, 100);

// Get velocity at keyframe
var velocity = prop.getVelocityAtKey(1);

// Set spatial tangents for Bezier interpolation
prop.setSpatialTangentsAtKey(1, [100, 0], [-100, 0]);  // inTangent, outTangent

// Get spatial tangents
var tangents = prop.getSpatialTangentsAtKey(1);
var inTangent = tangents[0];
var outTangent = tangents[1];

// Set temporal tangents
prop.setTemporalTangentsAtKey(1, [0.5, 0], [0.5, 0]);  // inTangent, outTangent
```

## Keyframe Timing

### Setting Keyframe Time

```javascript
var prop = layer.property("Position");

// Move keyframe to different time
prop.setKeyTime(1, 2.0);  // Move first keyframe to 2 seconds

// Get keyframe time
var time = prop.keyTime(1);
```

### Setting Keyframe Value

```javascript
var prop = layer.property("Position");

// Change keyframe value
prop.setKeyValue(1, [500, 540]);

// Get keyframe value
var value = prop.keyValue(1);
```

### Keyframe Duration

```javascript
var prop = layer.property("Position");

// Get duration between keyframes
if (prop.numKeys >= 2) {
    var key1Time = prop.keyTime(1);
    var key2Time = prop.keyTime(2);
    var duration = key2Time - key1Time;
    $.writeln("Duration: " + duration + " seconds");
}
```

## Keyframe Types

### Linear Keyframes

```javascript
var prop = layer.property("Position");

// Create linear keyframes
prop.setValueAtTime(0, [0, 540]);
prop.setValueAtTime(1, [960, 540]);
prop.setValueAtTime(2, [1920, 540]);

// Set all to linear
for (var i = 1; i <= prop.numKeys; i++) {
    prop.setTemporalInterpolationAtKey(i, KeyframeInterpolationType.LINEAR);
}
```

### Bezier Keyframes

```javascript
var prop = layer.property("Position");

// Create Bezier keyframes
prop.setValueAtTime(0, [0, 540]);
prop.setValueAtTime(2, [1920, 540]);

// Set Bezier interpolation
for (var i = 1; i <= prop.numKeys; i++) {
    prop.setTemporalInterpolationAtKey(i, KeyframeInterpolationType.BEZIER);
}

// Set ease
var easeIn = new KeyframeEase(0.33, 50);
var easeOut = new KeyframeEase(0.33, 50);
prop.setTemporalEaseAtKey(1, [easeIn], [easeOut]);
prop.setTemporalEaseAtKey(2, [easeIn], [easeOut]);
```

### Hold Keyframes

```javascript
var opacity = layer.property("Opacity");

// Create stepped animation
opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(1, 100);
opacity.setValueAtTime(2, 0);
opacity.setValueAtTime(3, 100);

// Set all to hold
for (var i = 1; i <= opacity.numKeys; i++) {
    opacity.setTemporalInterpolationAtKey(i, KeyframeInterpolationType.HOLD);
}
```

## Keyframe Manipulation

### Copy Keyframes

```javascript
function copyKeyframes(fromProp, toProp) {
    // Copy all keyframes
    for (var i = 1; i <= fromProp.numKeys; i++) {
        var time = fromProp.keyTime(i);
        var value = fromProp.keyValue(i);
        toProp.setValueAtTime(time, value);
    }
    
    // Copy interpolation types
    for (var i = 1; i <= fromProp.numKeys; i++) {
        var temporalType = fromProp.getTemporalInterpolationAtKey(i);
        toProp.setTemporalInterpolationAtKey(i, temporalType[0]);
        
        if (toProp.dimensions > 1) {
            var spatialType = fromProp.getSpatialInterpolationAtKey(i);
            toProp.setSpatialInterpolationAtKey(i, spatialType[0]);
        }
    }
}

// Usage
var pos1 = layer1.property("Position");
var pos2 = layer2.property("Position");
copyKeyframes(pos1, pos2);
```

### Offset Keyframes

```javascript
function offsetKeyframes(prop, offset) {
    // Store original keyframe data
    var keyframes = [];
    for (var i = 1; i <= prop.numKeys; i++) {
        keyframes.push({
            time: prop.keyTime(i),
            value: prop.keyValue(i)
        });
    }
    
    // Remove all keyframes
    while (prop.numKeys > 0) {
        prop.removeKey(1);
    }
    
    // Re-add with offset
    for (var i = 0; i < keyframes.length; i++) {
        prop.setValueAtTime(keyframes[i].time + offset, keyframes[i].value);
    }
}

// Usage
offsetKeyframes(layer.property("Position"), 1);  // Shift 1 second later
```

### Scale Keyframes

```javascript
function scaleKeyframes(prop, factor) {
    // Store original keyframe data
    var keyframes = [];
    for (var i = 1; i <= prop.numKeys; i++) {
        keyframes.push({
            time: prop.keyTime(i),
            value: prop.keyValue(i)
        });
    }
    
    // Get first keyframe time as reference
    var firstTime = keyframes[0].time;
    
    // Remove all keyframes
    while (prop.numKeys > 0) {
        prop.removeKey(1);
    }
    
    // Re-add with scaled times
    for (var i = 0; i < keyframes.length; i++) {
        var newTime = firstTime + (keyframes[i].time - firstTime) * factor;
        prop.setValueAtTime(newTime, keyframes[i].value);
    }
}

// Usage
scaleKeyframes(layer.property("Position"), 2);  // Double duration
```

### Reverse Keyframes

```javascript
function reverseKeyframes(prop) {
    // Store original keyframe data
    var keyframes = [];
    for (var i = 1; i <= prop.numKeys; i++) {
        keyframes.push({
            time: prop.keyTime(i),
            value: prop.keyValue(i)
        });
    }
    
    // Get time range
    var startTime = keyframes[0].time;
    var endTime = keyframes[keyframes.length - 1].time;
    var duration = endTime - startTime;
    
    // Remove all keyframes
    while (prop.numKeys > 0) {
        prop.removeKey(1);
    }
    
    // Re-add in reverse order
    for (var i = keyframes.length - 1; i >= 0; i--) {
        var newTime = startTime + (duration - (keyframes[i].time - startTime));
        prop.setValueAtTime(newTime, keyframes[i].value);
    }
}

// Usage
reverseKeyframes(layer.property("Position"));
```

## Keyframe Expressions

### Loop Keyframes

```javascript
var prop = layer.property("Position");

// Loop animation
prop.expression = "loopOut('cycle')";

// Options:
// 'cycle' - Repeat from start
// 'pingpong' - Alternate forward and backward
// 'offset' - Continue with offset
// 'continue' - Continue with same velocity
```

### Time Remapping

```javascript
var prop = layer.property("Time Remap");

// Set keyframes for time remapping
prop.setValueAtTime(0, 0);
prop.setValueAtTime(1, 2);  // Play 2 seconds in 1 second (2x speed)
prop.setValueAtTime(2, 3);  // Play 1 second in 1 second (normal speed)

// Enable time remapping
if (layer.canSetTimeRemapEnabled) {
    layer.timeRemapEnabled = true;
}
```

## Keyframe Utilities

### Get Keyframe Information

```javascript
function printKeyframeInfo(prop) {
    $.writeln("=== Keyframe Info for " + prop.name + " ===");
    $.writeln("Number of keyframes: " + prop.numKeys);
    
    for (var i = 1; i <= prop.numKeys; i++) {
        var time = prop.keyTime(i);
        var value = prop.keyValue(i);
        var temporalType = prop.getTemporalInterpolationAtKey(i);
        
        $.writeln("Key " + i + ":");
        $.writeln("  Time: " + time);
        $.writeln("  Value: " + value);
        $.writeln("  Temporal: " + temporalType[0]);
        
        if (prop.dimensions > 1) {
            var spatialType = prop.getSpatialInterpolationAtKey(i);
            $.writeln("  Spatial: " + spatialType[0]);
        }
    }
}

// Usage
printKeyframeInfo(layer.property("Position"));
```

### Smooth Keyframes

```javascript
function smoothKeyframes(prop, tension) {
    tension = tension || 0.5;  // Default tension
    
    for (var i = 2; i < prop.numKeys; i++) {
        var prevValue = prop.keyValue(i - 1);
        var currValue = prop.keyValue(i);
        var nextValue = prop.keyValue(i + 1);
        
        var prevTime = prop.keyTime(i - 1);
        var currTime = prop.keyTime(i);
        var nextTime = prop.keyTime(i + 1);
        
        // Calculate tangents
        var inTangent = [];
        var outTangent = [];
        
        for (var j = 0; j < prop.dimensions; j++) {
            var inSlope = (currValue[j] - prevValue[j]) / (currTime - prevTime);
            var outSlope = (nextValue[j] - currValue[j]) / (nextTime - currTime);
            
            inTangent[j] = (inSlope + outSlope) / 2 * tension;
            outTangent[j] = (inSlope + outSlope) / 2 * tension;
        }
        
        prop.setTemporalTangentsAtKey(i, [inTangent], [outTangent]);
    }
}

// Usage
smoothKeyframes(layer.property("Position"), 0.5);
```

### Quantize Keyframes

```javascript
function quantizeKeyframes(prop, frameRate) {
    frameRate = frameRate || 30;
    var frameDuration = 1 / frameRate;
    
    for (var i = 1; i <= prop.numKeys; i++) {
        var time = prop.keyTime(i);
        var quantizedTime = Math.round(time / frameDuration) * frameDuration;
        prop.setKeyTime(i, quantizedTime);
    }
}

// Usage
quantizeKeyframes(layer.property("Position"), 30);  // Snap to 30fps
```

## Common Patterns

### Bounce Animation

```javascript
var position = layer.property("Position");

position.setValueAtTime(0, [960, 0]);
position.setValueAtTime(0.3, [960, 540]);
position.setValueAtTime(0.45, [960, 490]);
position.setValueAtTime(0.6, [960, 540]);
position.setValueAtTime(0.7, [960, 520]);
position.setValueAtTime(0.8, [960, 540]);

// Set ease for natural bounce
var ease1 = new KeyframeEase(0.33, 50);
var ease2 = new KeyframeEase(0.33, 50);

for (var i = 1; i <= position.numKeys; i++) {
    position.setTemporalEaseAtKey(i, [ease1], [ease2]);
}
```

### Fade In/Out

```javascript
var opacity = layer.property("Opacity");

opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(0.5, 100);
opacity.setValueAtTime(2, 100);
opacity.setValueAtTime(2.5, 0);

// Set ease
var easeIn = new KeyframeEase(0.33, 50);
var easeOut = new KeyframeEase(0.33, 50);

opacity.setTemporalEaseAtKey(1, [easeIn], [easeOut]);
opacity.setTemporalEaseAtKey(2, [easeIn], [easeOut]);
opacity.setTemporalEaseAtKey(3, [easeIn], [easeOut]);
opacity.setTemporalEaseAtKey(4, [easeIn], [easeOut]);
```

### Scale Pulse

```javascript
var scale = layer.property("Scale");

scale.setValueAtTime(0, [100, 100]);
scale.setValueAtTime(0.5, [120, 120]);
scale.setValueAtTime(1, [100, 100]);

// Set ease
var easeIn = new KeyframeEase(0.5, 50);
var easeOut = new KeyframeEase(0.5, 50);

for (var i = 1; i <= scale.numKeys; i++) {
    scale.setTemporalEaseAtKey(i, [easeIn], [easeOut]);
}
```

### Rotation Spin

```javascript
var rotation = layer.property("Rotation");

rotation.setValueAtTime(0, 0);
rotation.setValueAtTime(2, 720);  // Two full rotations

// Set ease
var easeIn = new KeyframeEase(0.33, 50);
var easeOut = new KeyframeEase(0.33, 50);

rotation.setTemporalEaseAtKey(1, [easeIn], [easeOut]);
rotation.setTemporalEaseAtKey(2, [easeIn], [easeOut]);
```

### Path Animation

```javascript
var position = layer.property("Position");

// Create motion path
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(0.5, [480, 200]);
position.setValueAtTime(1, [960, 540]);
position.setValueAtTime(1.5, [1440, 880]);
position.setValueAtTime(2, [1920, 540]);

// Set Bezier spatial interpolation
for (var i = 1; i <= position.numKeys; i++) {
    position.setSpatialInterpolationAtKey(i, KeyframeSpatialInterpolationType.BEZIER);
}

// Set spatial tangents for smooth curve
position.setSpatialTangentsAtKey(1, [0, 0], [200, 0]);
position.setSpatialTangentsAtKey(2, [-200, 100], [200, -100]);
position.setSpatialTangentsAtKey(3, [-200, -100], [200, 100]);
position.setSpatialTangentsAtKey(4, [-200, 100], [200, -100]);
position.setSpatialTangentsAtKey(5, [-200, 0], [0, 0]);
```

## Best Practices

1. **Use `setValueAtTime()`** for creating keyframes
2. **Remove keyframes in reverse order** when deleting multiple
3. **Store keyframe data** before modifying
4. **Check `numKeys`** before accessing keyframes
5. **Use 1-based indices** for keyframe operations
6. **Set interpolation** after creating keyframes
7. **Use ease** for natural motion
8. **Use hold keyframes** for stepped animations
9. **Use expressions** for procedural animation
10. **Test at target frame rate** for timing accuracy

## Notes

- Keyframe indices are 1-based
- Adding/removing keyframes changes indices
- Temporal interpolation affects timing
- Spatial interpolation affects path shape
- Hold keyframes create stepped animation
- Bezier keyframes provide smooth curves
- Use `loopOut()` for repeating animations
- KeyframeEase controls velocity
- Tangents control Bezier curve shape
- Time is in seconds
