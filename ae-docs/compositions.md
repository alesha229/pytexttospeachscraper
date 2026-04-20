# Composition Creation

## Overview

Compositions (CompItem objects) are containers for layers and the fundamental unit of work in After Effects. Scripts can create, modify, and manage compositions programmatically to build complex scenes.

## Creating Compositions

### Basic Composition Creation

```javascript
// Create a new composition
var comp = app.project.items.addComp(
    "My Composition",   // Name
    1920,               // Width in pixels
    1080,               // Height in pixels
    1.0,                // Pixel aspect ratio
    10,                 // Duration in seconds
    30                  // Frame rate (fps)
);

// Set as active composition
app.project.activeItem = comp;
```

### Composition Settings Presets

```javascript
// HDTV 1080p
var compHD = app.project.items.addComp("HD Comp", 1920, 1080, 1.0, 10, 24);

// 4K UHD
var comp4K = app.project.items.addComp("4K Comp", 3840, 2160, 1.0, 10, 30);

// Square (for social media)
var compSquare = app.project.items.addComp("Square", 1080, 1080, 1.0, 5, 30);

// Vertical (for mobile/stories)
var compVertical = app.project.items.addComp("Vertical", 1080, 1920, 1.0, 5, 30);

// NTSC DV
var compNTSC = app.project.items.addComp("NTSC", 720, 480, 0.9091, 10, 29.97);

// PAL DV
var compPAL = app.project.items.addComp("PAL", 720, 576, 1.0667, 10, 25);
```

### Composition from Template

```javascript
// Create composition from template file
var templateFile = new File("/path/to/template.aet");
app.open(templateFile);

// Or use project items
var comp = app.project.item(1);  // Assuming first item is a comp
```

## CompItem Properties

### Basic Properties

```javascript
var comp = app.project.activeItem;

// Identification
comp.name = "New Composition Name";
var compId = comp.id;              // Unique ID (AE 22.0+)
var compIndex = comp.index;        // Index in project

// Dimensions
comp.width = 1920;
comp.height = 1080;

// Time properties
comp.duration = 30;                // Duration in seconds
comp.frameRate = 30;               // Frame rate
comp.frameDuration = 1/30;         // Duration of one frame

// Pixel aspect ratio
comp.pixelAspect = 1.0;            // 1.0 = square pixels
comp.pixelAspect = 0.9091;         // NTSC DV
comp.pixelAspect = 1.0667;         // PAL DV

// Background color (RGB 0.0-1.0)
comp.bgColor = [0, 0, 0];          // Black
comp.bgColor = [1, 1, 1];          // White
comp.bgColor = [0.2, 0.2, 0.2];    // Dark gray
```

### Work Area

```javascript
var comp = app.project.activeItem;

// Set work area
comp.workAreaStart = 0;            // Start time in seconds
comp.workAreaDuration = 10;        // Duration in seconds

// Get work area info
var start = comp.workAreaStart;
var duration = comp.workAreaDuration;
var end = start + duration;

// Set work area to selection
comp.workAreaStart = comp.displayStart;
comp.workAreaDuration = comp.displayDuration;
```

### Display Time

```javascript
var comp = app.project.activeItem;

// Set current display time
comp.displayTime = 5.0;            // 5 seconds

// Get current display time
var currentTime = comp.displayTime;

// Frame-based time
comp.displayStartFrame = 0;        // Start at frame 0
```

### Layer Management

```javascript
var comp = app.project.activeItem;

// Get number of layers
var numLayers = comp.numLayers;

// Access layers
var layer1 = comp.layer(1);        // Topmost layer
var lastLayer = comp.layer(comp.numLayers);

// Get layer by name
var namedLayer = comp.layer("My Layer");

// Get selected layers
var selectedLayers = comp.selectedLayers;
for (var i = 0; i < selectedLayers.length; i++) {
    $.writeln("Selected: " + selectedLayers[i].name);
}

// Get selected properties
var selectedProps = comp.selectedProperties;
```

### Markers

```javascript
var comp = app.project.activeItem;

// Create composition marker
var markerValue = new MarkerValue("Scene 1");
markerValue.duration = 5.0;
markerValue.chapter = "Chapter 1";

// Add marker at time
comp.markerProperty.setValueAtTime(0, markerValue);
comp.markerProperty.setValueAtTime(5, new MarkerValue("Scene 2"));
comp.markerProperty.setValueAtTime(10, new MarkerValue("Scene 3"));

// Access markers
var markerProp = comp.markerProperty;
for (var i = 1; i <= markerProp.numKeys; i++) {
    var time = markerProp.keyTime(i);
    var value = markerProp.keyValue(i);
    $.writeln("Marker at " + time + ": " + value.comment);
}
```

## Composition Settings

### Shutter Angle (Motion Blur)

```javascript
var comp = app.project.activeItem;

// Motion blur settings
comp.shutterAngle = 180;           // Degrees (default 180)
comp.shutterPhase = -90;           // Degrees (default -90)

// Motion blur samples
comp.motionBlurSamplesPerFrame = 16;   // Range: 2-64
comp.motionBlurAdaptiveSampleLimit = 256;  // Max samples
```

### Rendering Settings

```javascript
var comp = app.project.activeItem;

// Draft 3D mode
comp.draft3d = false;

// Frame blending
comp.frameBlending = false;

// Motion blur
comp.motionBlur = true;

// Preserve nested frame rates
comp.preserveNestedFrameRate = true;

// Preserve nested shutter angle
comp.preserveNestedShutterAngle = false;
```

### Environment

```javascript
var comp = app.project.activeItem;

// Ray-traced 3D renderer
comp.renderer = "RAYTRACE";        // "RAYTRACE" or "MAIN" (Classic 3D)

// Environment layer
var envLayer = comp.layers.addSolid([0.5, 0.5, 0.5], "Environment", 1920, 1080, 1.0);
envLayer.environmentLayer = true;
```

## Composition Operations

### Duplicating Compositions

```javascript
var comp = app.project.activeItem;

// Duplicate composition
var duplicate = comp.duplicate();
duplicate.name = comp.name + " Copy";
```

### Setting Active Composition

```javascript
var comp = app.project.items.addComp("Active Comp", 1920, 1080, 1.0, 10, 30);

// Set as active
app.project.activeItem = comp;

// Get active composition
var activeComp = app.project.activeItem;
if (activeComp instanceof CompItem) {
    $.writeln("Active: " + activeComp.name);
}
```

### Opening in Timeline

```javascript
var comp = app.project.activeItem;

// Open in timeline panel (opens UI)
comp.openInViewer();
```

### Removing Compositions

```javascript
var comp = app.project.activeItem;

// Remove from project
comp.remove();
```

## Nested Compositions

### Creating Pre-compositions

```javascript
var comp = app.project.activeItem;

// Select layers to pre-compose
var layerIndices = [1, 2, 3];

// Create pre-comp
var preComp = comp.layers.precompose(
    layerIndices,
    "Pre-comp",
    true                           // Move all attributes
);

// Access the pre-comp item
var preCompItem = preComp.source;
```

### Working with Nested Comps

```javascript
var comp = app.project.activeItem;

// Add composition as layer
var nestedComp = app.project.item(2);  // Assuming it's a comp
var nestedLayer = comp.layers.add(nestedComp);

// Access nested composition
var sourceComp = nestedLayer.source;
if (sourceComp instanceof CompItem) {
    $.writeln("Nested comp: " + sourceComp.name);
    $.writeln("Nested layers: " + sourceComp.numLayers);
}

// Replace nested composition source
var newComp = app.project.item(3);
nestedLayer.replaceSource(newComp, true);
```

### Time Remapping Nested Comps

```javascript
var nestedLayer = comp.layers.add(nestedComp);

// Enable time remapping
if (nestedLayer.canSetTimeRemapEnabled) {
    nestedLayer.timeRemapEnabled = true;
    
    // Access time remap property
    var timeRemap = nestedLayer.property("Time Remap");
    timeRemap.setValueAtTime(0, 0);
    timeRemap.setValueAtTime(2, 5);  // Play 5 seconds in 2 seconds
}
```

## Composition Utilities

### Finding Compositions

```javascript
// Get all compositions in project
function getAllComps() {
    var comps = [];
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem) {
            comps.push(item);
        }
    }
    return comps;
}

// Usage
var allComps = getAllComps();
for (var i = 0; i < allComps.length; i++) {
    $.writeln("Comp: " + allComps[i].name);
}

// Find composition by name
function findCompByName(name) {
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === name) {
            return item;
        }
    }
    return null;
}

// Usage
var myComp = findCompByName("Main Composition");
```

### Composition Information

```javascript
function printCompInfo(comp) {
    $.writeln("=== Composition Info ===");
    $.writeln("Name: " + comp.name);
    $.writeln("Dimensions: " + comp.width + "x" + comp.height);
    $.writeln("Duration: " + comp.duration + "s");
    $.writeln("Frame Rate: " + comp.frameRate + " fps");
    $.writeln("Pixel Aspect: " + comp.pixelAspect);
    $.writeln("Layers: " + comp.numLayers);
    $.writeln("Work Area: " + comp.workAreaStart + " - " + 
              (comp.workAreaStart + comp.workAreaDuration) + "s");
    $.writeln("Motion Blur: " + comp.motionBlur);
    $.writeln("Draft 3D: " + comp.draft3d);
    $.writeln("Renderer: " + comp.renderer);
}

// Usage
printCompInfo(app.project.activeItem);
```

### Batch Composition Creation

```javascript
// Create multiple compositions for different scenes
var sceneNames = ["Intro", "Main", "Outro"];
var sceneDurations = [5, 30, 5];

for (var i = 0; i < sceneNames.length; i++) {
    var comp = app.project.items.addComp(
        sceneNames[i],
        1920,
        1080,
        1.0,
        sceneDurations[i],
        30
    );
    
    // Add background solid
    var bg = comp.layers.addSolid([0.1, 0.1, 0.1], "Background", 1920, 1080, 1.0);
    bg.moveToBeginning();
}
```

## Rendering Compositions

### Add to Render Queue

```javascript
var comp = app.project.activeItem;

// Add to render queue
var renderQueue = app.project.renderQueue;
var rqItem = renderQueue.items.add(comp);

// Configure output settings
rqItem.outputModules[1].file = new File("/path/to/output.mov");
```

### Render Queue Item Properties

```javascript
var comp = app.project.activeItem;
var rqItem = app.project.renderQueue.items.add(comp);

// Time span
rqItem.timeSpanStart = 0;
rqItem.timeSpanDuration = comp.duration;

// Skip or include
rqItem.skip = false;

// Check status
var status = rqItem.status;
// RQItemStatus.QUEUED, RENDERING, DONE, WILL_CONTINUE, etc.
```

### Output Module Settings

```javascript
var rqItem = app.project.renderQueue.items.add(comp);
var outputModule = rqItem.outputModules[1];

// Set output file
outputModule.file = new File("/path/to/output.mov");

// Output module template
outputModule.applyTemplate("Lossless");

// Format
outputModule.format = "QuickTime";

// Format options
// outputModule.formatOptions...
```

## Composition Templates

### Save as Template

```javascript
// Save current composition as template
var comp = app.project.activeItem;

// Create template folder
var templateFolder = new Folder("/path/to/templates");
if (!templateFolder.exists) {
    templateFolder.create();
}

// Save project as template
app.project.save(new File(templateFolder.fsName + "/template.aet"));
```

### Using Composition Templates

```javascript
// Open template project
var templateFile = new File("/path/to/template.aet");
app.open(templateFile);

// Get the composition
var templateComp = app.project.item(1);

// Duplicate for use
var newComp = templateComp.duplicate();
newComp.name = "New Scene";
```

## Common Patterns

### Create Composition from Footage

```javascript
// Create composition matching footage properties
var footage = app.project.item(1);  // Assuming footage item

if (footage instanceof FootageItem) {
    var comp = app.project.items.addComp(
        footage.name,
        footage.width,
        footage.height,
        footage.pixelAspect,
        footage.duration,
        footage.frameRate
    );
    
    // Add footage as layer
    comp.layers.add(footage);
}
```

### Create Composition Grid

```javascript
// Create grid of compositions
var rows = 2;
var cols = 3;
var compWidth = 640;
var compHeight = 360;

for (var r = 0; r < rows; r++) {
    for (var c = 0; c < cols; c++) {
        var comp = app.project.items.addComp(
            "Grid_" + r + "_" + c,
            compWidth,
            compHeight,
            1.0,
            5,
            30
        );
        
        // Add colored background
        var bg = comp.layers.addSolid(
            [r/rows, c/cols, 0.5],
            "BG",
            compWidth,
            compHeight,
            1.0
        );
    }
}
```

### Composition Sequence

```javascript
// Create sequence of compositions
var compNames = ["Scene_01", "Scene_02", "Scene_03", "Scene_04"];
var transitionDuration = 1;
var currentTime = 0;

var mainComp = app.project.items.addComp("Main", 1920, 1080, 1.0, 30, 30);

for (var i = 0; i < compNames.length; i++) {
    // Create scene composition
    var sceneComp = app.project.items.addComp(
        compNames[i],
        1920,
        1080,
        1.0,
        5,
        30
    );
    
    // Add content to scene
    var bg = sceneComp.layers.addSolid(
        [Math.random(), Math.random(), Math.random()],
        "Background",
        1920,
        1080,
        1.0
    );
    
    // Add scene to main composition
    var sceneLayer = mainComp.layers.add(sceneComp);
    sceneLayer.startTime = currentTime;
    
    currentTime += 5 - transitionDuration;
}
```

### Composition Versioning

```javascript
// Create versioned compositions
var baseComp = app.project.activeItem;
var versions = ["v01", "v02", "v03"];

for (var i = 0; i < versions.length; i++) {
    var versionComp = baseComp.duplicate();
    versionComp.name = baseComp.name + "_" + versions[i];
    
    // Modify each version
    var titleLayer = versionComp.layer("Title");
    if (titleLayer) {
        var textProp = titleLayer.property("Source Text");
        var textDoc = textProp.value;
        textDoc.text = "Version " + versions[i];
        textProp.setValue(textDoc);
    }
}
```

## Best Practices

1. **Always check item types** before performing operations
2. **Use meaningful composition names** for better organization
3. **Set appropriate work areas** to limit rendering scope
4. **Store composition references** in variables instead of repeated lookups
5. **Validate composition dimensions** match intended output
6. **Use pixel aspect ratio** appropriate for target platform
7. **Organize compositions** using folders (FootageItem folders)
8. **Check for existing compositions** before creating duplicates
9. **Set motion blur settings** early in composition setup
10. **Use pre-compositions** to organize complex scenes

## Notes

- Composition indices in project are 1-based
- Layer indices within compositions are 1-based
- Duration is in seconds (not frames)
- Frame rate affects keyframe timing precision
- Pixel aspect ratio affects visual appearance
- Work area determines render range
- Nested compositions can affect performance
- Use `instanceof CompItem` to verify item type
- Composition background color is visible in transparent areas
- Renderer setting affects 3D capabilities
