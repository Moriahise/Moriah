import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
await build({entryPoints:[root+'src/integrations.mjs'],outfile:root+'assets/integrations.js',bundle:true,format:'iife',target:['es2020'],minify:true,legalComments:'eof'});
