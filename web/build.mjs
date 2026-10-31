import { mkdir, copyFile, cp } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
for (const file of ['index.html', 'experience.html', 'styles.css', 'motion.css', 'motion.js', 'app.js', 'i18n.js', 'intake.js', 'property.js']) {
  await copyFile(file, `dist/${file}`);
}
await cp('assets', 'dist/assets', { recursive: true });
for (const file of ['assistant.html', 'assistant.css', 'assistant.js']) {
  await copyFile(file, `dist/${file}`);
}
console.log('Built static site in web/dist');
