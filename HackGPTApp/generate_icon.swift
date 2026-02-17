#!/usr/bin/env swift
// Generates HackGPT.icns using native AppKit/CoreGraphics
import AppKit
import Foundation

func createIconImage(size: Int) -> NSImage {
    let s = CGFloat(size)
    let image = NSImage(size: NSSize(width: s, height: s))
    
    image.lockFocus()
    guard let ctx = NSGraphicsContext.current?.cgContext else {
        image.unlockFocus()
        return image
    }
    
    let margin = s * 0.06
    let corner = s * 0.22
    let rect = CGRect(x: margin, y: margin, width: s - margin * 2, height: s - margin * 2)
    
    // Background: dark rounded rectangle
    let bgPath = NSBezierPath(roundedRect: rect, xRadius: corner, yRadius: corner)
    NSColor(red: 0.06, green: 0.06, blue: 0.12, alpha: 1.0).setFill()
    bgPath.fill()
    
    // Border glow (red)
    NSColor(red: 0.85, green: 0.15, blue: 0.15, alpha: 0.8).setStroke()
    bgPath.lineWidth = max(1, s / 60)
    bgPath.stroke()
    
    // Inner border
    let innerMargin = margin + s * 0.02
    let innerRect = CGRect(x: innerMargin, y: innerMargin,
                            width: s - innerMargin * 2, height: s - innerMargin * 2)
    let innerPath = NSBezierPath(roundedRect: innerRect, xRadius: corner * 0.9, yRadius: corner * 0.9)
    NSColor(red: 0.80, green: 0.12, blue: 0.12, alpha: 0.4).setStroke()
    innerPath.lineWidth = max(0.5, s / 120)
    innerPath.stroke()
    
    let cx = s / 2
    let cy = s / 2
    
    // Shield shape (flipped coordinate system: origin bottom-left)
    let shieldW = s * 0.40
    let shieldH = s * 0.48
    let shieldTop = cy + shieldH * 0.38
    
    let shield = NSBezierPath()
    shield.move(to: NSPoint(x: cx, y: shieldTop))                                  // top center
    shield.line(to: NSPoint(x: cx + shieldW / 2, y: shieldTop - shieldH * 0.18))   // top right
    shield.line(to: NSPoint(x: cx + shieldW / 2, y: shieldTop - shieldH * 0.58))   // mid right
    shield.line(to: NSPoint(x: cx, y: shieldTop - shieldH))                        // bottom point
    shield.line(to: NSPoint(x: cx - shieldW / 2, y: shieldTop - shieldH * 0.58))   // mid left
    shield.line(to: NSPoint(x: cx - shieldW / 2, y: shieldTop - shieldH * 0.18))   // top left
    shield.close()
    
    NSColor(red: 0.10, green: 0.10, blue: 0.18, alpha: 0.9).setFill()
    shield.fill()
    NSColor(red: 0.85, green: 0.20, blue: 0.20, alpha: 1.0).setStroke()
    shield.lineWidth = max(1, s / 70)
    shield.stroke()
    
    // Terminal chevron ">" inside shield
    let chevSize = s * 0.08
    let chevX = cx - chevSize * 0.6
    let chevY = cy - chevSize * 0.15
    
    let chevron = NSBezierPath()
    chevron.move(to: NSPoint(x: chevX, y: chevY + chevSize * 0.5))
    chevron.line(to: NSPoint(x: chevX + chevSize * 0.65, y: chevY))
    chevron.line(to: NSPoint(x: chevX, y: chevY - chevSize * 0.5))
    NSColor(red: 0.0, green: 0.95, blue: 0.40, alpha: 1.0).setStroke()
    chevron.lineWidth = max(1.5, s / 55)
    chevron.lineCapStyle = .round
    chevron.lineJoinStyle = .round
    chevron.stroke()
    
    // Underscore cursor "_"
    let cursorPath = NSBezierPath()
    cursorPath.move(to: NSPoint(x: chevX + chevSize * 0.9, y: chevY - chevSize * 0.5))
    cursorPath.line(to: NSPoint(x: chevX + chevSize * 1.6, y: chevY - chevSize * 0.5))
    NSColor(red: 0.0, green: 0.95, blue: 0.40, alpha: 0.7).setStroke()
    cursorPath.lineWidth = max(1.5, s / 55)
    cursorPath.lineCapStyle = .round
    cursorPath.stroke()
    
    // Draw "H" text at top of shield
    let fontSize = s * 0.13
    let font = NSFont.systemFont(ofSize: fontSize, weight: .heavy)
    let hAttrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: NSColor(red: 0.90, green: 0.20, blue: 0.20, alpha: 1.0)
    ]
    let hStr = "H" as NSString
    let hSize = hStr.size(withAttributes: hAttrs)
    hStr.draw(at: NSPoint(x: cx - hSize.width / 2, y: shieldTop - shieldH * 0.32), withAttributes: hAttrs)
    
    // Draw "GPT" below H
    let smallSize = s * 0.065
    let smallFont = NSFont.systemFont(ofSize: smallSize, weight: .bold)
    let gptAttrs: [NSAttributedString.Key: Any] = [
        .font: smallFont,
        .foregroundColor: NSColor(red: 0.78, green: 0.78, blue: 0.82, alpha: 0.85)
    ]
    let gptStr = "GPT" as NSString
    let gptSize = gptStr.size(withAttributes: gptAttrs)
    gptStr.draw(at: NSPoint(x: cx - gptSize.width / 2, y: shieldTop - shieldH * 0.32 - hSize.height - s * 0.01),
                withAttributes: gptAttrs)
    
    // Subtle scan lines
    NSColor(red: 0.0, green: 0.7, blue: 0.4, alpha: 0.08).setStroke()
    for i in 0..<4 {
        let yLine = margin + s * 0.12 + CGFloat(i) * s * 0.22
        let line = NSBezierPath()
        line.move(to: NSPoint(x: margin + s * 0.06, y: yLine))
        line.line(to: NSPoint(x: s - margin - s * 0.06, y: yLine))
        line.lineWidth = 0.5
        line.stroke()
    }
    
    image.unlockFocus()
    return image
}

// Main
let iconsetDir = "/Users/user/HackGPT/HackGPTApp/HackGPT.iconset"
let fm = FileManager.default
try? fm.createDirectory(atPath: iconsetDir, withIntermediateDirectories: true)

let sizes: [(Int, String)] = [
    (16,   "icon_16x16.png"),
    (32,   "icon_16x16@2x.png"),
    (32,   "icon_32x32.png"),
    (64,   "icon_32x32@2x.png"),
    (128,  "icon_128x128.png"),
    (256,  "icon_128x128@2x.png"),
    (256,  "icon_256x256.png"),
    (512,  "icon_256x256@2x.png"),
    (512,  "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]

for (size, filename) in sizes {
    print("  Generating \(filename) (\(size)x\(size))...")
    let img = createIconImage(size: size)
    
    guard let tiff = img.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else {
        print("  ERROR: Failed to create PNG for \(filename)")
        continue
    }
    
    let path = (iconsetDir as NSString).appendingPathComponent(filename)
    try! png.write(to: URL(fileURLWithPath: path))
}

print("  Converting to .icns...")

let resourcesDir = "/Users/user/HackGPT/HackGPTApp/HackGPT.app/Contents/Resources"
try? fm.createDirectory(atPath: resourcesDir, withIntermediateDirectories: true)

let icnsPath = "\(resourcesDir)/AppIcon.icns"
let proc = Process()
proc.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
proc.arguments = ["-c", "icns", "-o", icnsPath, iconsetDir]
try! proc.run()
proc.waitUntilExit()

if proc.terminationStatus == 0 {
    print("  ✅ Icon created: \(icnsPath)")
    // Cleanup
    try? fm.removeItem(atPath: iconsetDir)
    print("  Cleaned up iconset")
} else {
    print("  ❌ iconutil failed")
}
