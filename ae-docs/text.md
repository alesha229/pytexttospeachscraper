# Text Layers

## Overview

Text layers contain text content with extensive formatting options. They support point text (single line) and paragraph text (box text with wrapping), with character and paragraph-level formatting, fonts, and advanced typography features.

## Text Layer Creation

### Creating Text Layers

```javascript
var comp = app.project.activeItem;

// Create point text layer (single line)
var textLayer = comp.layers.addText("Hello World");
textLayer.name = "Title";

// Create empty text layer
var textLayer2 = comp.layers.addText();
var textProp = textLayer2.property("Source Text");
var textDoc = new TextDocument("Custom Text");
textProp.setValue(textDoc);

// Create paragraph (box) text
var boxTextLayer = comp.layers.addBoxText([500, 300]);  // [width, height]
var textProp2 = boxTextLayer.property("Source Text");
var textDoc2 = textProp2.value;
textDoc2.text = "This is paragraph text with automatic wrapping.";
textProp2.setValue(textDoc2);
```

## TextDocument Object

### Creating TextDocument

```javascript
// Create with text
var textDoc = new TextDocument("Hello World");

// Create empty
var textDoc2 = new TextDocument();
textDoc2.text = "Hello World";
```

### TextDocument Properties

```javascript
var textDoc = new TextDocument("Sample Text");

// Text content
textDoc.text = "New Text Content";

// Font (PostScript font name)
textDoc.font = "ArialMT";           // Arial Regular
textDoc.font = "Arial-BoldMT";     // Arial Bold
textDoc.font = "Helvetica";        // Helvetica
textDoc.font = "TimesNewRomanPSMT"; // Times New Roman

// Font size (points)
textDoc.fontSize = 48;

// Fill color [R, G, B] 0.0-1.0
textDoc.fillColor = [1, 0, 0];     // Red
textDoc.fillColor = [0, 0, 0];     // Black
textDoc.applyFill = true;          // Enable fill

// Stroke color
textDoc.strokeColor = [0, 0, 0];   // Black
textDoc.strokeWidth = 2;           // Stroke width in pixels
textDoc.applyStroke = true;        // Enable stroke

// Tracking (letter spacing)
textDoc.tracking = 0;              // Normal
textDoc.tracking = 50;             // Wider spacing
textDoc.tracking = -20;            // Tighter spacing

// Leading (line spacing) - auto if null
textDoc.leading = null;            // Auto leading
textDoc.leading = 60;              // Fixed leading

// Character offset (baseline shift)
textDoc.baselineShift = 0;         // Normal
textDoc.baselineShift = 10;        // Superscript
textDoc.baselineShift = -10;       // Subscript

// Tsume (Japanese text spacing)
textDoc.tsume = 0;

// Horizontal scale (percentage)
textDoc.horizontalScale = 100;     // Normal
textDoc.horizontalScale = 150;     // Wider
textDoc.horizontalScale = 75;      // Condensed

// Vertical scale (percentage)
textDoc.verticalScale = 100;       // Normal
textDoc.verticalScale = 150;       // Taller

// Auto leading (percentage of font size)
textDoc.autoLeading = true;
textDoc.autoLeadingPercent = 120;  // 120% of font size

// Faux styles
textDoc.fauxBold = true;
textDoc.fauxItalic = true;
textDoc.fauxUnderline = false;
textDoc.fauxStrikethrough = false;

// Small caps
textDoc.smallCaps = false;

// All caps
textDoc.allCaps = false;

// Superscript/Subscript
textDoc.baselineLocation = BaselineLocation.NORMAL;
// Options: BaselineLocation.NORMAL, SUPERSCRIPT, SUBSCRIPT

// Ligatures
textDoc.ligature = true;

// Fractional widths
textDoc.fractionalWidths = true;

// No breaks (prevent line breaks)
textDoc.noBreak = false;
```

### TextDocument Methods

```javascript
var textDoc = new TextDocument("Hello World");

// Reset to default
textDoc.resetCharStyle();

// Reset paragraph style
textDoc.resetParagraphStyle();
```

## Text Layer Properties

### Source Text Property

```javascript
var textLayer = comp.layers.addText("Hello");
var textProp = textLayer.property("Source Text");

// Get current text document
var currentText = textProp.value;
$.writeln("Text: " + currentText.text);
$.writeln("Font: " + currentText.font);
$.writeln("Size: " + currentText.fontSize);

// Set new text document
var newText = new TextDocument("World");
newText.fontSize = 72;
newText.fillColor = [1, 1, 1];
textProp.setValue(newText);

// Set text at specific time (keyframe)
textProp.setValueAtTime(0, new TextDocument("Frame 1"));
textProp.setValueAtTime(2, new TextDocument("Frame 2"));
```

### Text Animators

```javascript
var textLayer = comp.layers.addText("Animate Me");
var textProp = textLayer.property("Source Text");

// Access text animators group
var animators = textLayer.property("Text");
var animatorCount = animators.numProperties;

// Add animator
var animator = animators.addProperty("ADBE Text Animator");
animator.name = "My Animator";

// Add selector to animator
var selector = animator.addProperty("ADBE Text Selector");
selector.name = "Range Selector";

// Add properties to animate
var animatorProps = animator.property("ADBE Text Properties");

// Add position animator
var posProp = animatorProps.addProperty("ADBE Text Position");
posProp.setValue([0, 100]);  // Animate position

// Add opacity animator
var opacityProp = animatorProps.addProperty("ADBE Text Opacity");
opacityProp.setValue(0);  // Fade out

// Add scale animator
var scaleProp = animatorProps.addProperty("ADBE Text Scale");
scaleProp.setValue([200, 200]);  // Scale up

// Add rotation animator
var rotProp = animatorProps.addProperty("ADBE Text Rotation");
rotProp.setValue(360);  // Rotate 360 degrees

// Add fill color animator
var colorProp = animatorProps.addProperty("ADBE Text Fill Color");
colorProp.setValue([1, 0, 0]);  // Red
```

### Text Selectors

```javascript
var animator = textLayer.property("Text").property("Animator 1");
var selector = animator.property("ADBE Text Selector");

// Range Selector properties
var start = selector.property("ADBE Text Selector Start");
var end = selector.property("ADBE Text Selector End");
var offset = selector.property("ADBE Text Selector Offset");

// Set range
start.setValue(0);     // Start at 0%
end.setValue(100);     // End at 100%

// Animate offset for scrolling effect
offset.setValueAtTime(0, -100);
offset.setValueAtTime(2, 100);

// Selector mode
var selectorMode = selector.property("ADBE Text Selector Mode");
selectorMode.setValue(1);  // 1=Add, 2=Subtract, 3=Intersect

// Selector shape
var selectorShape = selector.property("ADBE Text Selector Shape");
selectorShape.setValue(1);  // 1=Square, 2=Ramp Up, 3=Ramp Down, 4=Triangle, 5=Round

// Ease amounts
var easeHigh = selector.property("ADBE Text Selector Ease High");
var easeLow = selector.property("ADBE Text Selector Ease Low");
easeHigh.setValue(100);
easeLow.setValue(100);

// Randomize order
var randomize = selector.property("ADBE Text Selector Randomize Order");
randomize.setValue(true);

// Max/Min amount
var maxAmount = selector.property("ADBE Text Selector Max Amount");
maxAmount.setValue(100);
```

### Expression Selectors

```javascript
var animator = textLayer.property("Text").property("Animator 1");

// Add expression selector
var exprSelector = animator.addProperty("ADBE Text Expression Selector");
exprSelector.name = "Expression Selector";

// Set expression
var exprProp = exprSelector.property("ADBE Text Expression Selector Amount");
exprProp.expression = "Math.sin(time * 2 + textIndex * 0.5) * 100";

// Expression variables available:
// textIndex - character index
// textTotal - total characters
// time - current time
// value - current value
```

## Text Properties Group

### Accessing Text Properties

```javascript
var textLayer = comp.layers.addText("Hello");
var textGroup = textLayer.property("Text");

// Text animators
var animators = textGroup.property("ADBE Text Animators");

// Path options
var pathOptions = textGroup.property("ADBE Text Path Options");

// More options
var moreOptions = textGroup.property("ADBE Text More Options");
```

### Path Options

```javascript
var textLayer = comp.layers.addText("Curved Text");
var textGroup = textLayer.property("Text");
var pathOptions = textGroup.property("ADBE Text Path Options");

// Set path
var maskPath = textLayer.property("Masks").property("Mask 1").property("Mask Path");
pathOptions.property("ADBE Text Path").setValue(maskPath);

// Path options
pathOptions.property("ADBE Text Reverse Path").setValue(false);
pathOptions.property("ADBE Text Perpendicular To Path").setValue(true);
pathOptions.property("ADBE Text Force Align Path").setValue(false);
pathOptions.property("ADBE Text First Margin").setValue(0);
pathOptions.property("ADBE Text Last Margin").setValue(0);
```

### More Options

```javascript
var textLayer = comp.layers.addText("Text");
var textGroup = textLayer.property("Text");
var moreOptions = textGroup.property("ADBE Text More Options");

// Anchor point grouping
moreOptions.property("ADBE Text Anchor Point Grouping").setValue(1);
// Options: 1=Character, 2=Word, 3=Line, 4=All

// Grouping alignment
moreOptions.property("ADBE Text Grouping Alignment").setValue([0, 0]);

// Render order
moreOptions.property("ADBE Text Render Order").setValue(1);
// Options: 1=Characters, 2=Words, 3=Lines

// Character blend mode
moreOptions.property("ADBE Text Character Blend Mode").setValue(1);
// Options: 1=Normal, etc.
```

## Paragraph Text Properties

### Box Text Settings

```javascript
var boxTextLayer = comp.layers.addBoxText([500, 300]);
var textProp = boxTextLayer.property("Source Text");
var textDoc = textProp.value;

// Set text
textDoc.text = "This is paragraph text that will wrap within the box.";

// Box dimensions (set via layer, not TextDocument)
var boxWidth = 500;
var boxHeight = 300;

// Paragraph alignment
var paragraphGroup = boxTextLayer.property("Paragraph");
var alignment = paragraphGroup.property("ADBE Paragraph Justification");
alignment.setValue(1);  // 1=Left, 2=Center, 3=Right, 4=Justify

// First line indent
var firstIndent = paragraphGroup.property("ADBE Paragraph First Line Indent");
firstIndent.setValue(20);

// Left indent
var leftIndent = paragraphGroup.property("ADBE Paragraph Left Indent");
leftIndent.setValue(0);

// Right indent
var rightIndent = paragraphGroup.property("ADBE Paragraph Right Indent");
rightIndent.setValue(0);

// Space before
var spaceBefore = paragraphGroup.property("ADBE Paragraph Space Before");
spaceBefore.setValue(10);

// Space after
var spaceAfter = paragraphGroup.property("ADBE Paragraph Space After");
spaceAfter.setValue(10);
```

## Font Management

### Common Font Names

```javascript
// Arial
var arialRegular = "ArialMT";
var arialBold = "Arial-BoldMT";
var arialItalic = "Arial-ItalicMT";
var arialBoldItalic = "Arial-BoldItalicMT";

// Helvetica
var helveticaRegular = "Helvetica";
var helveticaBold = "Helvetica-Bold";
var helveticaLight = "Helvetica-Light";

// Times New Roman
var timesRegular = "TimesNewRomanPSMT";
var timesBold = "TimesNewRomanPS-BoldMT";
var timesItalic = "TimesNewRomanPS-ItalicMT";

// Courier
var courierRegular = "CourierNewPSMT";
var courierBold = "CourierNewPS-BoldMT";

// Georgia
var georgiaRegular = "Georgia";
var georgiaBold = "Georgia-Bold";

// Verdana
var verdanaRegular = "Verdana";
var verdanaBold = "Verdana-Bold";

// Impact
var impactRegular = "Impact";

// Comic Sans
var comicSans = "ComicSansMS";

// Trebuchet
var trebuchet = "TrebuchetMS";
```

### Using System Fonts

```javascript
// List available fonts (requires BridgeTalk or external query)
// Fonts must be installed on the system

// Check if font exists (by attempting to use it)
function testFont(fontName) {
    var textLayer = comp.layers.addText("Test");
    var textProp = textLayer.property("Source Text");
    var textDoc = textProp.value;
    textDoc.font = fontName;
    textProp.setValue(textDoc);
    
    // If no error, font exists
    return true;
}

// Usage
try {
    testFont("ArialMT");
    $.writeln("Arial is available");
} catch (e) {
    $.writeln("Arial is not available");
}
```

## Text Animation Presets

### Applying Text Presets

```javascript
var textLayer = comp.layers.addText("Animated Text");

// Apply animation preset
var presetFile = new File("/path/to/text preset.ffx");
textLayer.applyPreset(presetFile);
```

### Common Text Animation Types

```javascript
// Typewriter effect (manual)
var textLayer = comp.layers.addText("Typewriter Text");
var textProp = textLayer.property("Source Text");
var fullText = "This is a typewriter effect.";

// Create character-by-character reveal
var animator = textLayer.property("Text").addProperty("ADBE Text Animator");
var selector = animator.addProperty("ADBE Text Selector");
var end = selector.property("ADBE Text Selector End");

end.setValueAtTime(0, 0);
end.setValueAtTime(fullText.length * 0.1, 100);  // 0.1s per character

// Fade in word by word
var textLayer2 = comp.layers.addText("Fade In Words");
var animator2 = textLayer2.property("Text").addProperty("ADBE Text Animator");
var opacityProp = animator2.property("ADBE Text Properties").addProperty("ADBE Text Opacity");
opacityProp.setValue(0);

var selector2 = animator2.addProperty("ADBE Text Selector");
selector2.property("ADBE Text Selector Shape").setValue(2);  // Ramp Up
var offset2 = selector2.property("ADBE Text Selector Offset");
offset2.setValueAtTime(0, -100);
offset2.setValueAtTime(2, 100);
```

## Text Layer Styling

### Character Styles

```javascript
var textLayer = comp.layers.addText("Styled Text");
var textProp = textLayer.property("Source Text");
var textDoc = textProp.value;

// Bold text
textDoc.font = "Arial-BoldMT";
textDoc.fontSize = 48;
textDoc.fillColor = [1, 1, 1];  // White
textDoc.tracking = 50;

textProp.setValue(textDoc);

// Italic text
var textDoc2 = new TextDocument("Italic Text");
textDoc2.font = "Arial-ItalicMT";
textDoc2.fontSize = 36;
textDoc2.fillColor = [1, 0.5, 0];  // Orange
textDoc2.fauxItalic = true;

textProp.setValueAtTime(2, textDoc2);
```

### Multiple Styles in One Layer

```javascript
// Note: After Effects text layers support multiple styles via
// the text editor, but scripting sets uniform style via TextDocument
// For mixed styles, use multiple text layers or expressions

var textLayer1 = comp.layers.addText("Bold");
var textProp1 = textLayer1.property("Source Text");
var doc1 = textProp1.value;
doc1.font = "Arial-BoldMT";
doc1.fontSize = 48;
textProp1.setValue(doc1);

var textLayer2 = comp.layers.addText("Regular");
textLayer2.property("Source Text").value.font = "ArialMT";
textLayer2.startTime = 0.5;
textLayer2.property("Position").setValue([
    textLayer1.property("Position").value[0] + 100,
    textLayer1.property("Position").value[1]
]);
```

### Text with Stroke and Fill

```javascript
var textLayer = comp.layers.addText("Outlined Text");
var textProp = textLayer.property("Source Text");
var textDoc = textProp.value;

textDoc.font = "Arial-BoldMT";
textDoc.fontSize = 72;
textDoc.fillColor = [1, 1, 1];  // White fill
textDoc.applyFill = true;
textDoc.strokeColor = [0, 0, 0];  // Black stroke
textDoc.strokeWidth = 3;
textDoc.applyStroke = true;

textProp.setValue(textDoc);
```

### Text Shadow (via Layer Styles)

```javascript
var textLayer = comp.layers.addText("Shadow Text");

// Add drop shadow effect
var shadowEffect = textLayer.property("Effects").addProperty("ADBE Drop Shadow");
shadowEffect.property("ADBE Drop Shadow Distance").setValue(5);
shadowEffect.property("ADBE Drop Shadow Direction").setValue(135);
shadowEffect.property("ADBE Drop Shadow Color").setValue([0, 0, 0]);
shadowEffect.property("ADBE Drop Shadow Opacity").setValue(75);
shadowEffect.property("ADBE Drop Shadow Softness").setValue(5);
```

## Text Animation Examples

### Typewriter Effect

```javascript
var textLayer = comp.layers.addText("Typewriter Effect");
var textProp = textLayer.property("Source Text");
var fullText = "This text appears character by character.";

// Set initial empty text
var emptyDoc = new TextDocument("");
emptyDoc.font = "ArialMT";
emptyDoc.fontSize = 36;
emptyDoc.fillColor = [1, 1, 1];
textProp.setValue(emptyDoc);

// Add animator for reveal
var animator = textLayer.property("Text").addProperty("ADBE Text Animator");
var opacityProp = animator.property("ADBE Text Properties").addProperty("ADBE Text Opacity");
opacityProp.setValue(0);

var selector = animator.addProperty("ADBE Text Selector");
var end = selector.property("ADBE Text Selector End");

// Animate end value to reveal characters
var duration = fullText.length * 0.05;  // 50ms per character
end.setValueAtTime(0, 0);
end.setValueAtTime(duration, 100);

// Set final text
textProp.setValueAtTime(0, new TextDocument(fullText));
```

### Bouncing Text

```javascript
var textLayer = comp.layers.addText("Bounce");
var animator = textLayer.property("Text").addProperty("ADBE Text Animator");

// Add position animator
var posProp = animator.property("ADBE Text Properties").addProperty("ADBE Text Position");
posProp.setValue([0, -50]);  // Bounce up

// Add selector
var selector = animator.addProperty("ADBE Text Selector");
selector.property("ADBE Text Selector Shape").setValue(4);  // Triangle
selector.property("ADBE Text Selector Max Amount").setValue(100);

// Animate offset
var offset = selector.property("ADBE Text Selector Offset");
offset.setValueAtTime(0, -100);
offset.setValueAtTime(0.5, 0);
offset.setValueAtTime(1, 100);
```

### Color Cycling Text

```javascript
var textLayer = comp.layers.addText("Color Cycle");
var animator = textLayer.property("Text").addProperty("ADBE Text Animator");

// Add fill color animator
var colorProp = animator.property("ADBE Text Properties").addProperty("ADBE Text Fill Color");
colorProp.setValue([1, 0, 0]);  // Red

// Add selector
var selector = animator.addProperty("ADBE Text Selector");
selector.property("ADBE Text Selector Max Amount").setValue(100);

// Use expression for cycling
colorProp.expression = "[Math.sin(time) * 0.5 + 0.5, Math.sin(time + 2) * 0.5 + 0.5, Math.sin(time + 4) * 0.5 + 0.5]";
```

### Scrolling Text (Credits Style)

```javascript
var comp = app.project.activeItem;
var textLayer = comp.layers.addBoxText([800, 1080]);
var textProp = textLayer.property("Source Text");
var textDoc = textProp.value;

textDoc.text = "Scrolling Credits\n\nDirected by\nJohn Doe\n\nProduced by\nJane Smith\n\nWritten by\nBob Johnson";
textDoc.fontSize = 36;
textDoc.fillColor = [1, 1, 1];
textDoc.justification = ParagraphJustification.CENTER_JUSTIFY;
textProp.setValue(textDoc);

// Position text below comp
var position = textLayer.property("Position");
position.setValue([comp.width / 2, comp.height + 100]);

// Animate position
position.setValueAtTime(0, [comp.width / 2, comp.height + 100]);
position.setValueAtTime(10, [comp.width / 2, -200]);
```

### Glitch Text Effect

```javascript
var textLayer = comp.layers.addText("GLITCH");
var textProp = textLayer.property("Source Text");
var textDoc = textProp.value;
textDoc.font = "Arial-BoldMT";
textDoc.fontSize = 72;
textDoc.fillColor = [1, 1, 1];
textProp.setValue(textDoc);

// Add position wiggle
var position = textLayer.property("Position");
position.expression = "wiggle(10, 10)";

// Add opacity flicker
var opacity = textLayer.property("Opacity");
opacity.expression = "Math.random() > 0.7 ? 100 : 50";

// Add animator for color glitch
var animator = textLayer.property("Text").addProperty("ADBE Text Animator");
var colorProp = animator.property("ADBE Text Properties").addProperty("ADBE Text Fill Color");
colorProp.setValue([0, 1, 1]);  // Cyan

var selector = animator.addProperty("ADBE Text Expression Selector");
selector.property("ADBE Text Expression Selector Amount").expression = 
    "Math.random() > 0.9 ? 100 : 0";
```

## Text Utilities

### Measure Text Width

```javascript
// Approximate text width (requires estimation)
function estimateTextWidth(text, fontSize, fontName) {
    // Rough estimation - actual width depends on font metrics
    var avgCharWidth = fontSize * 0.6;  // Approximate average
    return text.length * avgCharWidth;
}

// Usage
var text = "Hello World";
var width = estimateTextWidth(text, 48, "ArialMT");
$.writeln("Approximate width: " + width);
```

### Create Text at Position

```javascript
function createTextAtPosition(comp, text, position, options) {
    options = options || {};
    options.fontSize = options.fontSize || 36;
    options.font = options.font || "ArialMT";
    options.color = options.color || [1, 1, 1];
    options.anchorPoint = options.anchorPoint || [0.5, 0.5];  // Center
    
    var textLayer = comp.layers.addText(text);
    var textProp = textLayer.property("Source Text");
    var textDoc = textProp.value;
    
    textDoc.fontSize = options.fontSize;
    textDoc.font = options.font;
    textDoc.fillColor = options.color;
    textProp.setValue(textDoc);
    
    textLayer.property("Position").setValue(position);
    
    // Set anchor point for centering
    textLayer.property("Anchor Point").setValue([0, 0]);
    
    return textLayer;
}

// Usage
createTextAtPosition(comp, "Center Text", [960, 540], {
    fontSize: 48,
    font: "Arial-BoldMT",
    color: [1, 1, 1]
});
```

### Text Fade In/Out

```javascript
function createTextFade(comp, text, startTime, duration, fadeDuration) {
    var textLayer = comp.layers.addText(text);
    var opacity = textLayer.property("Opacity");
    
    var inPoint = startTime;
    var outPoint = startTime + duration;
    
    opacity.setValueAtTime(inPoint, 0);
    opacity.setValueAtTime(inPoint + fadeDuration, 100);
    opacity.setValueAtTime(outPoint - fadeDuration, 100);
    opacity.setValueAtTime(outPoint, 0);
    
    return textLayer;
}

// Usage
createTextFade(comp, "Fade Text", 1, 3, 0.5);
```

## Best Practices

1. **Use TextDocument objects** for setting text properties
2. **Set all text properties** before calling setValue()
3. **Use PostScript font names** for consistency
4. **Consider using animators** for dynamic text effects
5. **Use box text** for multi-line or wrapped text
6. **Store text layer references** for later modification
7. **Use expressions** for procedural text animation
8. **Check font availability** on target systems
9. **Use tracking and leading** for better readability
10. **Organize complex text** with multiple layers vs mixed styles

## Notes

- Text layers support both point text and paragraph (box) text
- TextDocument objects are immutable - create new ones for changes
- Font names use PostScript naming convention
- Text animators provide powerful per-character animation
- Expression selectors allow procedural animation
- Fill and stroke colors use 0.0-1.0 RGB values
- Text can be animated along paths using masks
- Paragraph text supports alignment and indentation
- Text layers can have layer styles applied (drop shadow, etc.)
- Use `addText()` for point text, `addBoxText()` for paragraph text
