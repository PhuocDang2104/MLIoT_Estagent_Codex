import { mkdir, copyFile, cp } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
for (const file of ['index.html', 'experience.html', 'styles.css', 'motion.css', 'motion.js', 'app.js', 'i18n.js', 'intake.js', 'property.js', 'creator.html', 'viewer.html', 'tour.css', 'tour-common.js', 'creator.js', 'viewer.js', 'panorama.js']) {
  await copyFile(file, `dist/${file}`);
}
await cp('assets', 'dist/assets', { recursive: true });
for (const file of ['export.html', 'export.js', 'export.css', 'narration-panel.js', 'narration-panel.css', 'assistant.html', 'assistant.css', 'assistant.js', 'studio.html', 'studio.css', 'studio.js', 'studio-panorama.js', 'studio-tour.html', 'studio-tour.js']) {
  await copyFile(file, `dist/${file}`);
}
console.log('Built static site in web/dist');

await cp('demos', 'dist/demos', { recursive: true });
