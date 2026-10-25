const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { generateImageAsync, getPngInfo } = require('@expo/image-utils');

// Package the supplied artwork for launchers without redrawing or cropping it.
const projectRoot = path.resolve(__dirname, '..');
(async () => {
  for (const [name, padding] of [['pl-icon.png', 64], ['pl-adaptive-icon.png', 184]]) {
    const { source } = await generateImageAsync({ projectRoot }, {
      src: path.join(projectRoot, 'assets/pl-logo.jpg'),
      resizeMode: 'contain', width: 1024, height: 1024, padding,
      backgroundColor: '#F7F7F7', removeTransparency: true,
    });
    const file = path.join(projectRoot, 'assets', name);
    await fs.writeFile(file, source);
    const info = await getPngInfo(file);
    assert.equal(info.width, 1024); assert.equal(info.height, 1024);
    console.log(`Prepared ${name} (1024 × 1024)`);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
