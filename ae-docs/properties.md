# Property Animation

## Overview

Properties represent animatable attributes in After Effects (position, scale, rotation, opacity, effects parameters, etc.). Properties are accessed through PropertyGroup objects and can be keyframed, have expressions applied, and manipulated programmatically.

## Property Hierarchy

- **PropertyBase** (abstract base)
  - **PropertyGroup** (contains other properties)
    - Layer
    - MaskPropertyGroup
    - EffectPropertyGroup
    - TransformGroup
  - **Property** (animatable values)
    - PositionProperty
    - ScalarProperty
    - ColorProperty
    - etc.

## Accessing Properties

### From Layer Object

```javascript
var layer = comp.layer(1);

// Get transform group
var transform = layer.property("Transform");

// Access individual transform properties
var position = transform.property("Position");
var scale = transform.property("Scale");
var rotation = transform.property("Rotation");
var opacity = transform.property("Opacity");
var anchorPoint = transform.property("Anchor Point");

// 3D transform properties
var xPosition = transform.property("X Position");
var yPosition = transform.property("Y Position");
var zPosition = transform.property("Z Position");
var orientation = transform.property("Orientation");

// Alternative: Direct access from layer
var position2 = layer.property("Position");
var scale2 = layer.property("Scale");
```

### Using Property Index

```javascript
var transform = layer.property("Transform");

// Access by name
var position = transform.property("Position");

// Access by index (1-based)
var position2 = transform.property(1);

// Get property name from index
var propName = transform.propertyName(1);  // Returns "Position"

// Get number of properties in group
var numProps = transform.numProperties;
```

### Nested Property Access

```javascript
// Effects properties
var effect = layer.property("Effects").property("Blur");
var blurAmount = effect.property("Blurriness");

// Mask properties
var mask = layer.property("Masks").property("Mask 1");
var maskPath = mask.property("Mask Path");

// Shape layer properties
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var rectGroup = contents.property("Rectangle 1");
var rectPath = rectGroup.property("Rect Path");
var size = rectPath.property("Size");
```

### Using Match Names

```javascript
// Match names are language-independent identifiers
var position = layer.property("ADBE Transform Group").property("ADBE Position");
var scale = layer.property("ADBE Transform Group").property("ADBE Scale");
var rotation = layer.property("ADBE Transform Group").property("ADBE Rotate Z");
var opacity = layer.property("ADBE Transform Group").property("ADBE Opacity");
var anchorPoint = layer.property("ADBE Transform Group").property("ADBE Anchor Point");

// Shape layer match names
var contents = shapeLayer.property("ADBE Root Vectors Group");
var rectGroup = contents.property("ADBE Vector Group");
var rectPath = rectGroup.property("ADBE Vectors Group").property("ADBE Vector Shape - Rect");
```

## Property Attributes

### Basic Property Info

```javascript
var prop = layer.property("Position");

// Read-only identification
var name = prop.name;              // Display name
var matchName = prop.matchName;    // Language-independent name
var propertyIndex = prop.propertyIndex;
var propertyDepth = prop.propertyDepth;  // Nesting depth
var parentGroup = prop.parentProperty;   // Parent PropertyGroup

// Property type
var type = prop.propertyType;
// Options: PropertyType.PROPERTY, PropertyType.INDEXED_GROUP, PropertyType.NAMED_GROUP

// Data type
var valueType = prop.propertyValueType;
// Options: PropertyValueType.OneD, TwoD, ThreeD, FourD, Color, CustomValue, etc.
```

### Property State

```javascript
var prop = layer.property("Opacity");

// Check if property can be keyframed
var canKeyframe = prop.canSetExpression;

// Check if property has keyframes
var hasKeys = prop.numKeys > 0;

// Check if property is animated
var isAnimated = prop.isTimeVarying;

// Check if property is enabled
var isEnabled = prop.enabled;

// Check if property can have expression
var canHaveExpression = prop.canSetExpression;
```

### Property Dimensions

```javascript
var position = layer.property("Position");

// Get number of dimensions
var dimensions = position.dimensions;  // 2 for 2D, 3 for 3D

// Get property value type
var valueType = position.propertyValueType;
// PropertyValueType.ThreeD for position
// PropertyValueType.TwoD for scale (typically)
// PropertyValueType.OneD for opacity/rotation
```

## Getting and Setting Values

### Simple Values

```javascript
var opacity = layer.property("Opacity");
var rotation = layer.property("Rotation");

// Get current value
var currentOpacity = opacity.value;

// Set value
opacity.setValue(50);
rotation.setValue(45);

// Set at specific time (adds keyframe if property is animated)
opacity.setValueAtTime(1.0, 0);
opacity.setValueAtTime(2.0, 100);
```

### Multi-dimensional Values

```javascript
var position = layer.property("Position");
var scale = layer.property("Scale");
var anchorPoint = layer.property("Anchor Point");

// Set 2D values
position.setValue([960, 540]);
anchorPoint.setValue([0, 0]);

// Set 3D values (requires 3D layer enabled)
layer.threeDLayer = true;
position.setValue([960, 540, 0]);

// Scale is typically expressed as percentage
scale.setValue([100, 100]);

// Color values (RGBA, 0.0-1.0)
var solid = layer.property("Contents").property("Fill").property("Color");
solid.setValue([1, 0, 0, 1]);  // Red, full alpha
```

### Setting Values Over Time

```javascript
var position = layer.property("Position");

// Set multiple keyframes
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(1, [960, 540]);
position.setValueAtTime(2, [1920, 540]);

// Remove all keyframes and set static value
position.removeKey(1);  // Removes first keyframe
// Or remove all keys
while (position.numKeys > 0) {
    position.removeKey(1);
}
```

### Using Keyframe Indices

```javascript
var prop = layer.property("Position");

// Get number of keyframes
var numKeys = prop.numKeys;

// Get keyframe times
for (var i = 1; i <= prop.numKeys; i++) {
    var keyTime = prop.keyTime(i);
    var keyValue = prop.keyValue(i);
    $.writeln("Key " + i + " at " + keyTime + ": " + keyValue);
}

// Get keyframe index at specific time
var keyIndex = prop.nearestKeyIndex(1.5);

// Get time of specific keyframe
var time = prop.keyTime(1);

// Get value at specific keyframe
var value = prop.keyValue(1);
```

### Finding Nearest Keyframe

```javascript
var prop = layer.property("Position");
var currentTime = 1.5;

// Find nearest keyframe
var nearestIndex = prop.nearestKeyIndex(currentTime);
var nearestTime = prop.keyTime(nearestIndex);
var nearestValue = prop.keyValue(nearestIndex);

$.writeln("Nearest key at " + nearestTime + " with value " + nearestValue);
```

## Keyframe Manipulation

### Adding Keyframes

```javascript
var position = layer.property("Position");

// Add keyframe at time with value
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(1, [960, 540]);
position.setValueAtTime(2, [1920, 540]);

// Add keyframe (alternative method)
position.addKey(1.5);
position.setValueAtTime(1.5, [480, 540]);

// Insert keyframe between existing keyframes
position.addKey(0.5);
position.setValueAtTime(0.5, [240, 540]);
```

### Removing Keyframes

```javascript
var prop = layer.property("Position");

// Remove specific keyframe by index
prop.removeKey(1);  // Remove first keyframe

// Remove all keyframes
function removeAllKeys(prop) {
    while (prop.numKeys > 0) {
        prop.removeKey(1);
    }
}

// Remove keyframes in time range
function removeKeysInRange(prop, startTime, endTime) {
    for (var i = prop.numKeys; i >= 1; i--) {
        var keyTime = prop.keyTime(i);
        if (keyTime >= startTime && keyTime <= endTime) {
            prop.removeKey(i);
        }
    }
}
```

### Keyframe Interpolation

```javascript
var prop = layer.property("Position");

// Set temporal interpolation
prop.setTemporalInterpolationAtKey(1, KeyframeInterpolationType.LINEAR);
prop.setTemporalInterpolationAtKey(2, KeyframeInterpolationType.BEZIER);
prop.setTemporalInterpolationAtKey(3, KeyframeInterpolationType.HOLD);

// Options: KeyframeInterpolationType.LINEAR, BEZIER, HOLD

// Set spatial interpolation (for multi-dimensional properties)
prop.setSpatialInterpolationAtKey(1, KeyframeSpatialInterpolationType.LINEAR);
prop.setSpatialInterpolationAtKey(2, KeyframeSpatialInterpolationType.BEZIER);
prop.setSpatialInterpolationAtKey(3, KeyframeSpatialInterpolationType.AUTO_BEZIER);

// Options: KeyframeSpatialInterpolationType.LINEAR, BEZIER, AUTO_BEZIER, CLAMPED
```

### Keyframe Ease and Velocity

```javascript
var prop = layer.property("Position");

// Create KeyframeEase objects
var easeIn = new KeyframeEase(0.5, 50);   // influence, speed
var easeOut = new KeyframeEase(0.5, 50);

// Set ease for keyframe
prop.setTemporalEaseAtKey(1, [easeIn], [easeOut]);

// Get ease for keyframe
var inEase = prop.getTemporalEaseAtKey(1)[0];
var outEase = prop.getTemporalEaseAtKey(1)[1];

$.writeln("In influence: " + inEase.influence);
$.writeln("Out influence: " + outEase.influence);
```

### Keyframe Velocity

```javascript
var prop = layer.property("Position");

// Set velocity at keyframe
prop.setVelocityAtKey(1, 100);  // pixels per second

// Get velocity at keyframe
var velocity = prop.getVelocityAtKey(1);

// Set spatial tangents (for Bezier interpolation)
prop.setSpatialTangentsAtKey(1, [100, 0], [-100, 0]);  // inTangent, outTangent

// Get spatial tangents
var tangents = prop.getSpatialTangentsAtKey(1);
var inTangent = tangents[0];
var outTangent = tangents[1];
```

### Keyframe Temporal Control

```javascript
var prop = layer.property("Position");

// Set keyframe time
prop.setKeyTime(1, 2.0);  // Move first keyframe to 2 seconds

// Get keyframe time
var keyTime = prop.keyTime(1);

// Set keyframe value
prop.setKeyValue(1, [500, 540]);

// Get keyframe value
var keyValue = prop.keyValue(1);
```

## Expressions

### Setting Expressions

```javascript
var position = layer.property("Position");
var opacity = layer.property("Opacity");

// Enable expression
position.expressionEnabled = true;

// Set expression string
position.expression = "[time * 100, 540]";

// Expression for oscillating motion
opacity.expression = "50 + 50 * Math.sin(time * 2)";

// Reference another layer's property
position.expression = "thisComp.layer('Controller').transform.position";

// Disable expression
position.expressionEnabled = false;
```

### Expression Controls

```javascript
// Add expression control effect
var effect = layer.property("Effects").addProperty("ADBE Slider Control");
effect.name = "My Slider";

// Reference slider in expression
var otherProp = layer.property("Opacity");
otherProp.expression = "effect('My Slider')('Slider')";

// Common expression controls:
// - ADBE Slider Control (numeric slider)
// - ADBE Angle Control (angle picker)
// - ADBE Checkbox Control (boolean)
// - ADBE Color Control (color picker)
// - ADBE Point Control (2D point)
// - ADBE Layer Control (layer picker)
```

### Expression Syntax Examples

```javascript
// Wiggle
position.expression = "wiggle(2, 50)";

// Loop
position.expression = "loopOut('cycle')";

// Time-based
rotation.expression = "time * 90";

// Conditional
opacity.expression = "if (time > 2) 100 else 0";

// Linear interpolation
position.expression = "linear(time, 0, 2, [0, 540], [1920, 540])";

// Ease interpolation
position.expression = "ease(time, 0, 2, [0, 540], [1920, 540])";

// Access marker
position.expression = "marker.key(1).time";
```

### Expression Errors

```javascript
var prop = layer.property("Position");

// Check for expression errors
if (prop.expressionEnabled) {
    try {
        prop.expression = "invalid syntax";
    } catch (e) {
        $.writeln("Expression error: " + e.message);
    }
}

// Get expression error text
var errorText = prop.expressionError;
```

## Property Separation

### Separating Dimensions

```javascript
var position = layer.property("Position");

// Check if dimensions are separated
var separated = position.dimensionsSeparated;

// Separate dimensions (creates X Position, Y Position, Z Position)
if (!separated && position.canSeparateDimensions) {
    position.separateDimensions();
}

// Access separated properties
var xPos = layer.property("X Position");
var yPos = layer.property("Y Position");
var zPos = layer.property("Z Position");
```

## Property Enable/Disable

```javascript
var prop = layer.property("Motion Blur");

// Check if property can be enabled
if (prop.canSetEnabled) {
    prop.enabled = true;
}

// Toggle property
prop.enabled = !prop.enabled;
```

## Property Value Types

### OneD (Single Dimension)

```javascript
var opacity = layer.property("Opacity");
var rotation = layer.property("Rotation");

opacity.setValue(50);
var value = opacity.value;  // Returns number
```

### TwoD (Two Dimensions)

```javascript
var scale = layer.property("Scale");
scale.setValue([100, 100]);
var value = scale.value;  // Returns [x, y] array
```

### ThreeD (Three Dimensions)

```javascript
layer.threeDLayer = true;
var position = layer.property("Position");
position.setValue([960, 540, 0]);
var value = position.value;  // Returns [x, y, z] array
```

### FourD (Four Dimensions)

```javascript
// Rare, but used for certain properties
```

### Color

```javascript
var fillColor = shapeLayer.property("Contents")
    .property("Rectangle 1")
    .property("Fill 1")
    .property("Color");

fillColor.setValue([1, 0, 0, 1]);  // [R, G, B, A] 0.0-1.0
var color = fillColor.value;  // Returns [r, g, b, a] array
```

### NoValue (Custom Properties)

```javascript
// Some properties don't have simple values (like shape paths)
var shapePath = rectGroup.property("Rect Path");
// Access via shape object
var shape = shapePath.value;
```

## Common Patterns

### Animate Position Across Screen

```javascript
var comp = app.project.activeItem;
var solid = comp.layers.addSolid([1, 0, 0], "Animated", 100, 100, 1.0);
var position = solid.property("Position");

// Create movement animation
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(1, [960, 540]);
position.setValueAtTime(2, [1920, 540]);

// Set easing
position.setTemporalInterpolationAtKey(1, KeyframeInterpolationType.BEZIER);
position.setTemporalInterpolationAtKey(2, KeyframeInterpolationType.BEZIER);
position.setTemporalInterpolationAtKey(3, KeyframeInterpolationType.BEZIER);

// Add ease
var ease1 = new KeyframeEase(0.33, 50);
var ease2 = new KeyframeEase(0.33, 50);
position.setTemporalEaseAtKey(1, [ease1], [ease2]);
```

### Fade In/Out

```javascript
var opacity = layer.property("Opacity");

opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(0.5, 100);
opacity.setValueAtTime(2, 100);
opacity.setValueAtTime(2.5, 0);
```

### Scale Pulse

```javascript
var scale = layer.property("Scale");

scale.setValueAtTime(0, [100, 100]);
scale.setValueAtTime(0.5, [120, 120]);
scale.setValueAtTime(1, [100, 100]);
```

### Create Bounce Animation

```javascript
var position = layer.property("Position");
var startY = 540;
var endY = 300;

position.setValueAtTime(0, [960, startY]);
position.setValueAtTime(0.3, [960, endY]);
position.setValueAtTime(0.45, [960, startY + 50]);
position.setValueAtTime(0.6, [960, endY + 25]);
position.setValueAtTime(0.7, [960, startY]);

// Set hold keyframes for bounce effect
for (var i = 1; i <= position.numKeys; i++) {
    if (i % 2 === 0) {
        position.setTemporalInterpolationAtKey(i, KeyframeInterpolationType.HOLD);
    }
}
```

### Copy Keyframes Between Properties

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
        var spatialType = fromProp.getSpatialInterpolationAtKey(i);
        
        toProp.setTemporalInterpolationAtKey(i, temporalType[0]);
        if (toProp.dimensions > 1) {
            toProp.setSpatialInterpolationAtKey(i, spatialType[0]);
        }
    }
}

// Usage
var pos1 = layer1.property("Position");
var pos2 = layer2.property("Position");
copyKeyframes(pos1, pos2);
```

### Create Smooth Animation with Ease

```javascript
function createSmoothAnimation(prop, startTime, endTime, startValue, endValue) {
    prop.setValueAtTime(startTime, startValue);
    prop.setValueAtTime(endTime, endValue);
    
    var numKeys = prop.numKeys;
    var easeIn = new KeyframeEase(0.33, 50);
    var easeOut = new KeyframeEase(0.33, 50);
    
    prop.setTemporalEaseAtKey(numKeys - 1, [easeIn], [easeOut]);
    prop.setTemporalEaseAtKey(numKeys, [easeIn], [easeOut]);
}

// Usage
var position = layer.property("Position");
createSmoothAnimation(position, 0, 2, [0, 540], [1920, 540]);
```

## Best Practices

1. **Use match names** for language-independent scripts
2. **Check property types** before setting values
3. **Validate keyframe indices** before accessing keyframe data
4. **Handle separated dimensions** appropriately
5. **Use try-catch** when setting expressions to catch syntax errors
6. **Remove keyframes in reverse order** when deleting multiple keyframes
7. **Store property references** in variables for cleaner code
8. **Check `canSetEnabled`** before toggling property enabled state
9. **Use `setValueAtTime()`** for keyframing, `setValue()` for static values
10. **Consider using expressions** for procedural animation instead of keyframes

## Notes

- Property indices are 1-based (not 0)
- Keyframe indices are also 1-based
- Adding/removing keyframes changes indices of subsequent keyframes
- Some properties require 3D layer to be enabled
- Expression syntax uses JavaScript with After Effects-specific extensions
- Color values use 0.0-1.0 range (not 0-255)
- Position values are in composition coordinates
- Scale values are percentages (100 = original size)
- Rotation values are in degrees
- Opacity values are 0-100 (not 0-1)
