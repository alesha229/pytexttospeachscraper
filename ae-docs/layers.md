# Layer Creation and Manipulation

## Overview

Layers are the fundamental building blocks of After Effects compositions. The Layer object provides access to layers within compositions and can be accessed from an item's layer collection either by index number or by a name string.

## Layer Hierarchy

- **Layer** (base class)
  - **AVLayer** (audio-visual layers)
    - TextLayer
    - ShapeLayer
    - CameraLayer
    - LightLayer
  - **ThreeDModelLayer**

## Creating Layers

### LayerCollection Methods

Layers are created through the LayerCollection object accessed via `comp.layers`:

#### Add Solid Layer
```javascript
var comp = app.project.activeItem;
var solidLayer = comp.layers.addSolid(
    [1, 1, 1],      // Color [R, G, B] (0.0-1.0)
    "My Solid",      // Name
    1920,            // Width in pixels
    1080,            // Height in pixels
    1.0,             // Pixel aspect ratio
    10               // Duration in seconds (optional)
);
```

#### Add Null Layer
```javascript
var nullLayer = comp.layers.addNull(10); // Duration in seconds (optional)
nullLayer.name = "Controller";
```

#### Add Shape Layer
```javascript
var shapeLayer = comp.layers.addShape();
shapeLayer.name = "My Shape";
```

#### Add Text Layer (Point Text)
```javascript
var textLayer = comp.layers.addText("Hello World");
textLayer.name = "Title Text";
```

#### Add Text Layer with TextDocument
```javascript
var textLayer = comp.layers.addText();
var textProp = textLayer.property("Source Text");
var textDoc = new TextDocument("Custom Text");
textDoc.fontSize = 48;
textDoc.fillColor = [1, 0, 0]; // Red
textProp.setValue(textDoc);
```

#### Add Paragraph (Box) Text
```javascript
var boxTextLayer = comp.layers.addBoxText([500, 300]); // [width, height]
var textProp = boxTextLayer.property("Source Text");
var textDoc = textProp.value;
textDoc.text = "This is paragraph text with wrapping.";
textProp.setValue(textDoc);
```

#### Add Camera Layer
```javascript
var camera = comp.layers.addCamera(
    "My Camera",              // Name
    [comp.width/2, comp.height/2]  // Center point [x, y]
);
```

#### Add Light Layer
```javascript
var light = comp.layers.addLight(
    "My Light",               // Name
    [comp.width/2, comp.height/2]  // Center point [x, y]
);
light.property("Intensity").setValue(100);
```

#### Add Footage/Comp Layer
```javascript
// Add existing footage or composition
var footageItem = app.project.item(2); // Assuming item 2 is footage
var footageLayer = comp.layers.add(footageItem);
```

## Layer Properties and Attributes

### Basic Layer Attributes

```javascript
var layer = comp.layer(1);

// Name and identification
layer.name = "My Layer";
var layerIndex = layer.index;        // Read-only
var layerId = layer.id;              // Unique persistent ID (AE 22.0+)

// Time properties
layer.startTime = 2.0;               // Start time in seconds
layer.inPoint = 1.0;                 // In point in seconds
layer.outPoint = 11.0;               // Out point in seconds
var currentTime = layer.time;        // Read-only current time

// Duration and stretch
layer.stretch = 100;                 // Time stretch percentage (100 = normal)

// Visibility
layer.enabled = true;                // Enable/disable layer
layer.solo = false;                  // Solo the layer
layer.shy = false;                   // Hide shy layers
layer.locked = false;                // Lock/unlock layer

// Label color (0-16, 0=None, 1-16=preset colors)
layer.label = 5;

// Comment
layer.comment = "Layer notes";
```

### Layer Positioning

```javascript
// Move layer in stack
layer.moveToBeginning();             // Move to top
layer.moveToEnd();                   // Move to bottom
layer.moveAfter(otherLayer);         // Move after specified layer
layer.moveBefore(otherLayer);        // Move before specified layer

// Duplicate layer
var duplicate = layer.duplicate();

// Copy layer to another composition
layer.copyToComp(targetComp);

// Remove layer
layer.remove();
```

### Parent-Child Relationships

```javascript
// Set parent (with automatic offset adjustment)
childLayer.parent = parentLayer;

// Set parent without changing transform (may cause visual jump)
childLayer.setParentWithJump(parentLayer);

// Remove parent
childLayer.parent = null;

// Check if layer has parent
if (layer.parent !== null) {
    var parentName = layer.parent.name;
}
```

### Layer Orientation

```javascript
// Auto-orient layer
layer.autoOrient = AutoOrientType.ALONG_PATH;
// Options:
// - AutoOrientType.ALONG_PATH
// - AutoOrientType.CAMERA_OR_POINT_OF_INTEREST
// - AutoOrientType.CHARACTERS_TOWARD_CAMERA
// - AutoOrientType.NO_AUTO_ORIENT
```

### AVLayer-Specific Attributes

```javascript
var avLayer = comp.layers.addSolid([1,1,1], "Solid", 1920, 1080, 1.0);

// Layer type flags
avLayer.adjustmentLayer = true;      // Make adjustment layer
avLayer.nullLayer;                   // Read-only: true if null layer
avLayer.hasVideo;                    // Read-only: has video switch
avLayer.hasAudio;                    // Read-only: contains audio

// 3D Layer
avLayer.threeDLayer = true;          // Enable 3D
avLayer.threeDPerChar = true;        // Per-character 3D (text only)
avLayer.environmentLayer = true;     // Environment layer (ray-traced 3D)

// Quality and Sampling
avLayer.quality = LayerQuality.BEST;
// Options: LayerQuality.BEST, DRAFT, WIREFRAME

avLayer.samplingQuality = LayerSamplingQuality.BICUBIC;
// Options: LayerSamplingQuality.BICUBIC, BILINEAR

// Blending Mode
avLayer.blendingMode = BlendingMode.MULTIPLY;
// Options include: NORMAL, MULTIPLY, SCREEN, OVERLAY, ADD, etc.

// Time Remapping
if (avLayer.canSetTimeRemapEnabled) {
    avLayer.timeRemapEnabled = true;
}

// Frame Blending
avLayer.frameBlending;               // Read-only: is frame blending on
avLayer.frameBlendingType = FrameBlendingType.PIXEL_MOTION;
// Options: FrameBlendingType.NO_FRAME_BLEND, FRAME_MIX, PIXEL_MOTION

// Motion Blur
avLayer.motionBlur = true;

// Collapse Transformation
if (avLayer.canSetCollapseTransformation) {
    avLayer.collapseTransformation = true;
}

// Guide Layer
avLayer.guideLayer = true;

// Preserve Transparency
avLayer.preserveTransparency = true;

// Effects Active
avLayer.effectsActive = true;

// Track Matte (AE 23.0+)
if (avLayer.hasTrackMatte) {
    var matteLayer = avLayer.trackMatteLayer;
    var matteType = avLayer.trackMatteType;
}

// Set track matte
avLayer.setTrackMatte(matteLayer, TrackMatteType.ALPHA);
// Options: ALPHA, ALPHA_INVERTED, LUMA, LUMA_INVERTED

// Remove track matte
avLayer.removeTrackMatte();

// Dimensions
var width = avLayer.width;           // Read-only
var height = avLayer.height;         // Read-only
```

### Audio Properties

```javascript
// Audio enable/disable
avLayer.audioEnabled = true;
avLayer.audioActive;                 // Read-only: is audio active at current time

// Check if audio active at specific time
if (avLayer.audioActiveAtTime(5.0)) {
    // Audio is playing at 5 seconds
}
```

## Accessing Layers

### By Index
```javascript
// Get first layer (topmost)
var layer1 = comp.layer(1);

// Get last layer (bottommost)
var lastLayer = comp.layer(comp.numLayers);

// Get layer relative to another
var layer2 = comp.layer(layer1, 1);  // Layer after layer1
```

### By Name
```javascript
var layer = comp.layer("My Layer");
```

### Using LayerCollection Methods
```javascript
// Get layer by name (returns first match or null)
var layer = comp.layers.byName("My Layer");

// Get all layers
for (var i = 1; i <= comp.numLayers; i++) {
    var layer = comp.layer(i);
    $.writeln("Layer " + i + ": " + layer.name);
}

// Get selected layers
var selectedLayers = comp.selectedLayers;
for (var i = 0; i < selectedLayers.length; i++) {
    $.writeln("Selected: " + selectedLayers[i].name);
}
```

### Check Layer Activity
```javascript
// Check if layer is active at time
if (layer.activeAtTime(5.0)) {
    // Layer is visible/active at 5 seconds
}
```

## Layer Markers

```javascript
// Create layer marker
var markerValue = new MarkerValue("Marker Text");
markerValue.duration = 2.0;          // Duration in seconds
markerValue.url = "http://example.com";
markerValue.frameTarget = "frame1";
markerValue.cuePointName = "cue1";
markerValue.chapter = "Chapter 1";

// Add marker at time
layer.marker.setValueAtTime(1.0, markerValue);

// Access markers
var markerProp = layer.marker;
if (markerProp && markerProp.numKeys > 0) {
    for (var i = 1; i <= markerProp.numKeys; i++) {
        var time = markerProp.keyTime(i);
        var value = markerProp.keyValue(i);
        $.writeln("Marker at " + time + ": " + value.comment);
    }
}
```

## Pre-composing Layers

```javascript
// Pre-compose layers
var layerIndices = [1, 2, 3];        // Layer indices to pre-compose
var newComp = comp.layers.precompose(
    layerIndices,
    "Pre-comp Name",
    true                             // Move all attributes (default)
);

// Pre-compose leaving attributes
var newComp2 = comp.layers.precompose(
    [2],
    "Pre-comp 2",
    false                            // Leave attributes in original comp
);
```

## Applying Presets

```javascript
// Apply animation preset to layer
var presetFile = new File("/path/to/preset.ffx");
layer.applyPreset(presetFile);
```

## Working with Layer Source

```javascript
// Get source footage
var source = avLayer.source;         // AVItem object

// Replace source
var newFootage = app.project.item(3);
avLayer.replaceSource(newFootage, true);  // Fix expressions
```

## Layer Transform Access

```javascript
// Access transform properties
var transform = layer.property("Transform");
var position = transform.property("Position");
var scale = transform.property("Scale");
var rotation = transform.property("Rotation");
var opacity = transform.property("Opacity");
var anchorPoint = transform.property("Anchor Point");

// Set values
position.setValue([960, 540]);
scale.setValue([100, 100]);
rotation.setValue(45);
opacity.setValue(100);
anchorPoint.setValue([0, 0]);
```

## Common Patterns

### Create Multiple Solids in Grid
```javascript
var comp = app.project.activeItem;
var rows = 3;
var cols = 4;
var solidWidth = 200;
var solidHeight = 150;

for (var r = 0; r < rows; r++) {
    for (var c = 0; c < cols; c++) {
        var x = c * solidWidth + solidWidth/2;
        var y = r * solidHeight + solidHeight/2;
        
        var solid = comp.layers.addSolid(
            [Math.random(), Math.random(), Math.random()],
            "Solid_" + r + "_" + c,
            solidWidth,
            solidHeight,
            1.0
        );
        
        solid.property("Position").setValue([x, y]);
    }
}
```

### Organize Layers with Parenting
```javascript
// Create parent controller
var parent = comp.layers.addNull();
parent.name = "Master Controller";

// Parent multiple layers
for (var i = 1; i <= 5; i++) {
    var layer = comp.layers.addSolid([1,1,1], "Child " + i, 200, 200, 1.0);
    layer.parent = parent;
    layer.property("Position").setValue([i * 200, 540]);
}

// Animate parent to affect all children
parent.property("Position").setValueAtTime(0, [0, 0]);
parent.property("Position").setValueAtTime(2, [100, 100]);
```

### Layer Management Utilities
```javascript
// Find all layers of specific type
function findLayersByType(comp, type) {
    var results = [];
    for (var i = 1; i <= comp.numLayers; i++) {
        var layer = comp.layer(i);
        if (layer instanceof type) {
            results.push(layer);
        }
    }
    return results;
}

// Usage
var textLayers = findLayersByType(comp, TextLayer);
var shapeLayers = findLayersByType(comp, ShapeLayer);
```

## Best Practices

1. **Always check layer types** before performing type-specific operations
2. **Use meaningful names** for layers to improve script maintainability
3. **Group related layers** using pre-compose or null parent controllers
4. **Check if operations are valid** (e.g., `canSetTimeRemapEnabled`)
5. **Handle layer indices carefully** - they change when layers are added/removed
6. **Use `layer.id`** (AE 22.0+) for persistent layer identification
7. **Store layer references** in variables rather than repeatedly querying by index

## Notes

- Layer indices start at 1 (not 0)
- Adding/removing layers changes indices of other layers
- Layer.parent automatically adjusts child transforms to prevent jumping
- Use `setParentWithJump()` when you don't want automatic adjustment
- Null layers are invisible but useful for parenting and expressions
- Adjustment layers apply effects to all layers below them
