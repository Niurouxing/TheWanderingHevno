### package.json
```

{
  "name": "hevno",
  "version": "1.0.0",
  "private": true, 
  "scripts": {
    "dev": "concurrently \"pnpm:dev:schemas\" \"pnpm:dev:api\" \"pnpm:dev:web\"",
    "dev:schemas": "pnpm --filter @hevno/schemas dev",
    "dev:api": "pnpm --filter @hevno/api-server dev",
    "dev:web": "pnpm --filter @hevno/web-client dev",
    "build": "pnpm --filter \"@hevno/*\" build"
  },
  "devDependencies": {
    "concurrently": "^8.2.2",
    "typescript": "^5.4.5"
  }
}
```

### pnpm-workspace.yaml
```
# pnpm-workspace.yaml
packages:
  - 'packages/*' # 我们的核心代码库
  - 'plugins/*'   # 第三方或自定义插件
```

### packages/api-server/package.json
```

{
    "name": "@hevno/api-server",
    "version": "1.0.0",
    "type": "module",
    "main": "dist/index.js",
    "scripts": {
        "build": "tsc",
        "start": "node dist/index.js",
       "dev": "ts-node-dev --respawn --transpile-only --esm -- ./src/index.ts"
    },
    "dependencies": {
        "@fastify/cors": "^9.0.1",
        "@hevno/core-engine": "workspace:*",
        "@hevno/schemas": "workspace:*",
        "fastify": "^4.27.0",
        "socket.io": "^4.7.5",
        "zod": "^3.23.8"
    },
    "devDependencies": {
        "@types/node": "^20.12.12",
        "ts-node": "^10.9.2", 
        "ts-node-dev": "^2.0.0",
        "typescript": "^5.4.5"
    }
}
```

### packages/api-server/tsconfig.json
```
{
  "compilerOptions": {
    /* Visit https://aka.ms/tsconfig to read more about this file */

    /* Projects */
    // "incremental": true,                              /* Save .tsbuildinfo files to allow for incremental compilation of projects. */
    // "composite": true,                                /* Enable constraints that allow a TypeScript project to be used with project references. */
    // "tsBuildInfoFile": "./.tsbuildinfo",              /* Specify the path to .tsbuildinfo incremental compilation file. */
    // "disableSourceOfProjectReferenceRedirect": true,  /* Disable preferring source files instead of declaration files when referencing composite projects. */
    // "disableSolutionSearching": true,                 /* Opt a project out of multi-project reference checking when editing. */
    // "disableReferencedProjectLoad": true,             /* Reduce the number of projects loaded automatically by TypeScript. */

    /* Language and Environment */
    "target": "es2022",                                  /* Set the JavaScript language version for emitted JavaScript and include compatible library declarations. */
    // "lib": [],                                        /* Specify a set of bundled library declaration files that describe the target runtime environment. */
    // "jsx": "preserve",                                /* Specify what JSX code is generated. */
    // "libReplacement": true,                           /* Enable lib replacement. */
    // "experimentalDecorators": true,                   /* Enable experimental support for legacy experimental decorators. */
    // "emitDecoratorMetadata": true,                    /* Emit design-type metadata for decorated declarations in source files. */
    // "jsxFactory": "",                                 /* Specify the JSX factory function used when targeting React JSX emit, e.g. 'React.createElement' or 'h'. */
    // "jsxFragmentFactory": "",                         /* Specify the JSX Fragment reference used for fragments when targeting React JSX emit e.g. 'React.Fragment' or 'Fragment'. */
    // "jsxImportSource": "",                            /* Specify module specifier used to import the JSX factory functions when using 'jsx: react-jsx*'. */
    // "reactNamespace": "",                             /* Specify the object invoked for 'createElement'. This only applies when targeting 'react' JSX emit. */
    // "noLib": true,                                    /* Disable including any library files, including the default lib.d.ts. */
    // "useDefineForClassFields": true,                  /* Emit ECMAScript-standard-compliant class fields. */
    // "moduleDetection": "auto",                        /* Control what method is used to detect module-format JS files. */

    /* Modules */
    "module": "NodeNext",                                 /* Specify what module code is generated. */
    "rootDir": "src",                                    /* Specify the root folder within your source files. */
    "moduleResolution": "NodeNext",                    /* Specify how TypeScript looks up a file from a given module specifier. */
    // "baseUrl": "./",                                  /* Specify the base directory to resolve non-relative module names. */
    // "paths": {},                                      /* Specify a set of entries that re-map imports to additional lookup locations. */
    // "rootDirs": [],                                   /* Allow multiple folders to be treated as one when resolving modules. */
    // "typeRoots": [],                                  /* Specify multiple folders that act like './node_modules/@types'. */
    // "types": [],                                      /* Specify type package names to be included without being referenced in a source file. */
    // "allowUmdGlobalAccess": true,                     /* Allow accessing UMD globals from modules. */
    // "moduleSuffixes": [],                             /* List of file name suffixes to search when resolving a module. */
    // "allowImportingTsExtensions": true,               /* Allow imports to include TypeScript file extensions. Requires '--moduleResolution bundler' and either '--noEmit' or '--emitDeclarationOnly' to be set. */
    // "rewriteRelativeImportExtensions": true,          /* Rewrite '.ts', '.tsx', '.mts', and '.cts' file extensions in relative import paths to their JavaScript equivalent in output files. */
    // "resolvePackageJsonExports": true,                /* Use the package.json 'exports' field when resolving package imports. */
    // "resolvePackageJsonImports": true,                /* Use the package.json 'imports' field when resolving imports. */
    // "customConditions": [],                           /* Conditions to set in addition to the resolver-specific defaults when resolving imports. */
    // "noUncheckedSideEffectImports": true,             /* Check side effect imports. */
    "resolveJsonModule": true,                           /* Enable importing .json files. */
    // "allowArbitraryExtensions": true,                 /* Enable importing files with any extension, provided a declaration file is present. */
    // "noResolve": true,                                /* Disallow 'import's, 'require's or '<reference>'s from expanding the number of files TypeScript should add to a project. */

    /* JavaScript Support */
    // "allowJs": true,                                  /* Allow JavaScript files to be a part of your program. Use the 'checkJS' option to get errors from these files. */
    // "checkJs": true,                                  /* Enable error reporting in type-checked JavaScript files. */
    // "maxNodeModuleJsDepth": 1,                        /* Specify the maximum folder depth used for checking JavaScript files from 'node_modules'. Only applicable with 'allowJs'. */

    /* Emit */
    // "declaration": true,                              /* Generate .d.ts files from TypeScript and JavaScript files in your project. */
    // "declarationMap": true,                           /* Create sourcemaps for d.ts files. */
    // "emitDeclarationOnly": true,                      /* Only output d.ts files and not JavaScript files. */
    "sourceMap": true,                                   /* Create source map files for emitted JavaScript files. */
    // "inlineSourceMap": true,                          /* Include sourcemap files inside the emitted JavaScript. */
    // "noEmit": true,                                   /* Disable emitting files from a compilation. */
    // "outFile": "./",                                  /* Specify a file that bundles all outputs into one JavaScript file. If 'declaration' is true, also designates a file that bundles all .d.ts output. */
    "outDir": "dist",                                    /* Specify an output folder for all emitted files. */
    // "removeComments": true,                           /* Disable emitting comments. */
    // "importHelpers": true,                            /* Allow importing helper functions from tslib once per project, instead of including them per-file. */
    // "downlevelIteration": true,                       /* Emit more compliant, but verbose and less performant JavaScript for iteration. */
    // "sourceRoot": "",                                 /* Specify the root path for debuggers to find the reference source code. */
    // "mapRoot": "",                                    /* Specify the location where debugger should locate map files instead of generated locations. */
    // "inlineSources": true,                            /* Include source code in the sourcemaps inside the emitted JavaScript. */
    // "emitBOM": true,                                  /* Emit a UTF-8 Byte Order Mark (BOM) in the beginning of output files. */
    // "newLine": "crlf",                                /* Set the newline character for emitting files. */
    // "stripInternal": true,                            /* Disable emitting declarations that have '@internal' in their JSDoc comments. */
    // "noEmitHelpers": true,                            /* Disable generating custom helper functions like '__extends' in compiled output. */
    // "noEmitOnError": true,                            /* Disable emitting files if any type checking errors are reported. */
    // "preserveConstEnums": true,                       /* Disable erasing 'const enum' declarations in generated code. */
    // "declarationDir": "./",                           /* Specify the output directory for generated declaration files. */

    /* Interop Constraints */
    // "isolatedModules": true,                          /* Ensure that each file can be safely transpiled without relying on other imports. */
    // "verbatimModuleSyntax": true,                     /* Do not transform or elide any imports or exports not marked as type-only, ensuring they are written in the output file's format based on the 'module' setting. */
    // "isolatedDeclarations": true,                     /* Require sufficient annotation on exports so other tools can trivially generate declaration files. */
    // "erasableSyntaxOnly": true,                       /* Do not allow runtime constructs that are not part of ECMAScript. */
    // "allowSyntheticDefaultImports": true,             /* Allow 'import x from y' when a module doesn't have a default export. */
    "esModuleInterop": true,                             /* Emit additional JavaScript to ease support for importing CommonJS modules. This enables 'allowSyntheticDefaultImports' for type compatibility. */
    // "preserveSymlinks": true,                         /* Disable resolving symlinks to their realpath. This correlates to the same flag in node. */
    "forceConsistentCasingInFileNames": true,            /* Ensure that casing is correct in imports. */

    /* Type Checking */
    "strict": true,                                      /* Enable all strict type-checking options. */
    // "noImplicitAny": true,                            /* Enable error reporting for expressions and declarations with an implied 'any' type. */
    // "strictNullChecks": true,                         /* When type checking, take into account 'null' and 'undefined'. */
    // "strictFunctionTypes": true,                      /* When assigning functions, check to ensure parameters and the return values are subtype-compatible. */
    // "strictBindCallApply": true,                      /* Check that the arguments for 'bind', 'call', and 'apply' methods match the original function. */
    // "strictPropertyInitialization": true,             /* Check for class properties that are declared but not set in the constructor. */
    // "strictBuiltinIteratorReturn": true,              /* Built-in iterators are instantiated with a 'TReturn' type of 'undefined' instead of 'any'. */
    // "noImplicitThis": true,                           /* Enable error reporting when 'this' is given the type 'any'. */
    // "useUnknownInCatchVariables": true,               /* Default catch clause variables as 'unknown' instead of 'any'. */
    // "alwaysStrict": true,                             /* Ensure 'use strict' is always emitted. */
    // "noUnusedLocals": true,                           /* Enable error reporting when local variables aren't read. */
    // "noUnusedParameters": true,                       /* Raise an error when a function parameter isn't read. */
    // "exactOptionalPropertyTypes": true,               /* Interpret optional property types as written, rather than adding 'undefined'. */
    // "noImplicitReturns": true,                        /* Enable error reporting for codepaths that do not explicitly return in a function. */
    // "noFallthroughCasesInSwitch": true,               /* Enable error reporting for fallthrough cases in switch statements. */
    // "noUncheckedIndexedAccess": true,                 /* Add 'undefined' to a type when accessed using an index. */
    // "noImplicitOverride": true,                       /* Ensure overriding members in derived classes are marked with an override modifier. */
    // "noPropertyAccessFromIndexSignature": true,       /* Enforces using indexed accessors for keys declared using an indexed type. */
    // "allowUnusedLabels": true,                        /* Disable error reporting for unused labels. */
    // "allowUnreachableCode": true,                     /* Disable error reporting for unreachable code. */

    /* Completeness */
    // "skipDefaultLibCheck": true,                      /* Skip type checking .d.ts files that are included with TypeScript. */
    "skipLibCheck": true                                 /* Skip type checking all .d.ts files. */
  }
}

```

### packages/core-engine/package.json
```

{
  "name": "@hevno/core-engine",
  "type": "module",
  "version": "1.0.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "dependencies": {
    "@hevno/schemas": "workspace:*"
  },
  "devDependencies": {
    "@types/node": "^20.12.12"
  }
}
```

### packages/core-engine/tsconfig.json
```
{
  "compilerOptions": {
    /* Visit https://aka.ms/tsconfig to read more about this file */

    /* Projects */
    // "incremental": true,                              /* Save .tsbuildinfo files to allow for incremental compilation of projects. */
    // "composite": true,                                /* Enable constraints that allow a TypeScript project to be used with project references. */
    // "tsBuildInfoFile": "./.tsbuildinfo",              /* Specify the path to .tsbuildinfo incremental compilation file. */
    // "disableSourceOfProjectReferenceRedirect": true,  /* Disable preferring source files instead of declaration files when referencing composite projects. */
    // "disableSolutionSearching": true,                 /* Opt a project out of multi-project reference checking when editing. */
    // "disableReferencedProjectLoad": true,             /* Reduce the number of projects loaded automatically by TypeScript. */

    /* Language and Environment */
    "target": "es2022",                                  /* Set the JavaScript language version for emitted JavaScript and include compatible library declarations. */
    // "lib": [],                                        /* Specify a set of bundled library declaration files that describe the target runtime environment. */
    // "jsx": "preserve",                                /* Specify what JSX code is generated. */
    // "libReplacement": true,                           /* Enable lib replacement. */
    // "experimentalDecorators": true,                   /* Enable experimental support for legacy experimental decorators. */
    // "emitDecoratorMetadata": true,                    /* Emit design-type metadata for decorated declarations in source files. */
    // "jsxFactory": "",                                 /* Specify the JSX factory function used when targeting React JSX emit, e.g. 'React.createElement' or 'h'. */
    // "jsxFragmentFactory": "",                         /* Specify the JSX Fragment reference used for fragments when targeting React JSX emit e.g. 'React.Fragment' or 'Fragment'. */
    // "jsxImportSource": "",                            /* Specify module specifier used to import the JSX factory functions when using 'jsx: react-jsx*'. */
    // "reactNamespace": "",                             /* Specify the object invoked for 'createElement'. This only applies when targeting 'react' JSX emit. */
    // "noLib": true,                                    /* Disable including any library files, including the default lib.d.ts. */
    // "useDefineForClassFields": true,                  /* Emit ECMAScript-standard-compliant class fields. */
    // "moduleDetection": "auto",                        /* Control what method is used to detect module-format JS files. */

    /* Modules */
    "module": "NodeNext",                               /* Specify what module code is generated. */
    "rootDir": "src",                                    /* Specify the root folder within your source files. */
    "moduleResolution": "NodeNext",                     /* Specify how TypeScript looks up a file from a given module specifier. */
    // "baseUrl": "./",                                  /* Specify the base directory to resolve non-relative module names. */
    // "paths": {},                                      /* Specify a set of entries that re-map imports to additional lookup locations. */
    // "rootDirs": [],                                   /* Allow multiple folders to be treated as one when resolving modules. */
    // "typeRoots": [],                                  /* Specify multiple folders that act like './node_modules/@types'. */
    // "types": [],                                      /* Specify type package names to be included without being referenced in a source file. */
    // "allowUmdGlobalAccess": true,                     /* Allow accessing UMD globals from modules. */
    // "moduleSuffixes": [],                             /* List of file name suffixes to search when resolving a module. */
    // "allowImportingTsExtensions": true,               /* Allow imports to include TypeScript file extensions. Requires '--moduleResolution bundler' and either '--noEmit' or '--emitDeclarationOnly' to be set. */
    // "rewriteRelativeImportExtensions": true,          /* Rewrite '.ts', '.tsx', '.mts', and '.cts' file extensions in relative import paths to their JavaScript equivalent in output files. */
    // "resolvePackageJsonExports": true,                /* Use the package.json 'exports' field when resolving package imports. */
    // "resolvePackageJsonImports": true,                /* Use the package.json 'imports' field when resolving imports. */
    // "customConditions": [],                           /* Conditions to set in addition to the resolver-specific defaults when resolving imports. */
    // "noUncheckedSideEffectImports": true,             /* Check side effect imports. */
    "resolveJsonModule": true,                           /* Enable importing .json files. */
    // "allowArbitraryExtensions": true,                 /* Enable importing files with any extension, provided a declaration file is present. */
    // "noResolve": true,                                /* Disallow 'import's, 'require's or '<reference>'s from expanding the number of files TypeScript should add to a project. */

    /* JavaScript Support */
    // "allowJs": true,                                  /* Allow JavaScript files to be a part of your program. Use the 'checkJS' option to get errors from these files. */
    // "checkJs": true,                                  /* Enable error reporting in type-checked JavaScript files. */
    // "maxNodeModuleJsDepth": 1,                        /* Specify the maximum folder depth used for checking JavaScript files from 'node_modules'. Only applicable with 'allowJs'. */

    /* Emit */
    "declaration": true,                                 /* Generate .d.ts files from TypeScript and JavaScript files in your project. */
    // "declarationMap": true,                           /* Create sourcemaps for d.ts files. */
    // "emitDeclarationOnly": true,                      /* Only output d.ts files and not JavaScript files. */
    "sourceMap": true,                                   /* Create source map files for emitted JavaScript files. */
    // "inlineSourceMap": true,                          /* Include sourcemap files inside the emitted JavaScript. */
    // "noEmit": true,                                   /* Disable emitting files from a compilation. */
    // "outFile": "./",                                  /* Specify a file that bundles all outputs into one JavaScript file. If 'declaration' is true, also designates a file that bundles all .d.ts output. */
    "outDir": "dist",                                    /* Specify an output folder for all emitted files. */
    // "removeComments": true,                           /* Disable emitting comments. */
    // "importHelpers": true,                            /* Allow importing helper functions from tslib once per project, instead of including them per-file. */
    // "downlevelIteration": true,                       /* Emit more compliant, but verbose and less performant JavaScript for iteration. */
    // "sourceRoot": "",                                 /* Specify the root path for debuggers to find the reference source code. */
    // "mapRoot": "",                                    /* Specify the location where debugger should locate map files instead of generated locations. */
    // "inlineSources": true,                            /* Include source code in the sourcemaps inside the emitted JavaScript. */
    // "emitBOM": true,                                  /* Emit a UTF-8 Byte Order Mark (BOM) in the beginning of output files. */
    // "newLine": "crlf",                                /* Set the newline character for emitting files. */
    // "stripInternal": true,                            /* Disable emitting declarations that have '@internal' in their JSDoc comments. */
    // "noEmitHelpers": true,                            /* Disable generating custom helper functions like '__extends' in compiled output. */
    // "noEmitOnError": true,                            /* Disable emitting files if any type checking errors are reported. */
    // "preserveConstEnums": true,                       /* Disable erasing 'const enum' declarations in generated code. */
    // "declarationDir": "./",                           /* Specify the output directory for generated declaration files. */

    /* Interop Constraints */
    // "isolatedModules": true,                          /* Ensure that each file can be safely transpiled without relying on other imports. */
    // "verbatimModuleSyntax": true,                     /* Do not transform or elide any imports or exports not marked as type-only, ensuring they are written in the output file's format based on the 'module' setting. */
    // "isolatedDeclarations": true,                     /* Require sufficient annotation on exports so other tools can trivially generate declaration files. */
    // "erasableSyntaxOnly": true,                       /* Do not allow runtime constructs that are not part of ECMAScript. */
    // "allowSyntheticDefaultImports": true,             /* Allow 'import x from y' when a module doesn't have a default export. */
    "esModuleInterop": true,                             /* Emit additional JavaScript to ease support for importing CommonJS modules. This enables 'allowSyntheticDefaultImports' for type compatibility. */
    // "preserveSymlinks": true,                         /* Disable resolving symlinks to their realpath. This correlates to the same flag in node. */
    "forceConsistentCasingInFileNames": true,            /* Ensure that casing is correct in imports. */

    /* Type Checking */
    "strict": true,                                      /* Enable all strict type-checking options. */
    // "noImplicitAny": true,                            /* Enable error reporting for expressions and declarations with an implied 'any' type. */
    // "strictNullChecks": true,                         /* When type checking, take into account 'null' and 'undefined'. */
    // "strictFunctionTypes": true,                      /* When assigning functions, check to ensure parameters and the return values are subtype-compatible. */
    // "strictBindCallApply": true,                      /* Check that the arguments for 'bind', 'call', and 'apply' methods match the original function. */
    // "strictPropertyInitialization": true,             /* Check for class properties that are declared but not set in the constructor. */
    // "strictBuiltinIteratorReturn": true,              /* Built-in iterators are instantiated with a 'TReturn' type of 'undefined' instead of 'any'. */
    // "noImplicitThis": true,                           /* Enable error reporting when 'this' is given the type 'any'. */
    // "useUnknownInCatchVariables": true,               /* Default catch clause variables as 'unknown' instead of 'any'. */
    // "alwaysStrict": true,                             /* Ensure 'use strict' is always emitted. */
    // "noUnusedLocals": true,                           /* Enable error reporting when local variables aren't read. */
    // "noUnusedParameters": true,                       /* Raise an error when a function parameter isn't read. */
    // "exactOptionalPropertyTypes": true,               /* Interpret optional property types as written, rather than adding 'undefined'. */
    // "noImplicitReturns": true,                        /* Enable error reporting for codepaths that do not explicitly return in a function. */
    // "noFallthroughCasesInSwitch": true,               /* Enable error reporting for fallthrough cases in switch statements. */
    // "noUncheckedIndexedAccess": true,                 /* Add 'undefined' to a type when accessed using an index. */
    // "noImplicitOverride": true,                       /* Ensure overriding members in derived classes are marked with an override modifier. */
    // "noPropertyAccessFromIndexSignature": true,       /* Enforces using indexed accessors for keys declared using an indexed type. */
    // "allowUnusedLabels": true,                        /* Disable error reporting for unused labels. */
    // "allowUnreachableCode": true,                     /* Disable error reporting for unreachable code. */

    /* Completeness */
    // "skipDefaultLibCheck": true,                      /* Skip type checking .d.ts files that are included with TypeScript. */
    "skipLibCheck": true                                 /* Skip type checking all .d.ts files. */
  }
}

```

### packages/schemas/package.json
```
{
    "name": "@hevno/schemas",
    "version": "1.0.0",
    "type": "module",
    "main": "./dist/index.js",
    "types": "./dist/index.d.ts",
    "exports": {
        ".": {
            "import": "./dist/index.js",
            "require": "./dist/index.js",
            "types": "./dist/index.d.ts"
        }
    },
    "scripts": {
        "build": "tsc",
        "dev": "tsc --watch"
    },
    "dependencies": {
        "zod": "^3.23.8"
    },
    "devDependencies": {
    }
}

```

### packages/schemas/tsconfig.json
```
// packages/schemas/tsconfig.json
{
  "compilerOptions": {
    /* Visit https://aka.ms/tsconfig to read more about this file */

    /* Language and Environment */
    "target": "es2022",                                  /* Set the JavaScript language version for emitted JavaScript and include compatible library declarations. */

    /* Modules */
    "module": "NodeNext",
    "moduleResolution": "NodeNext",                                /* Specify what module code is generated. */
    "rootDir": "./src",                                  /* Specify the root folder within your source files. */

    /* Emitting Files */
    "declaration": true,                                 /* Generate .d.ts files from TypeScript and JavaScript files in your project. */
    "emitDeclarationOnly": false,                         /* Only output d.ts files and not JavaScript files. */
    "outDir": "./dist",                                  /* Specify an output folder for all emitted files. */

    /* Interop Constraints */
    "esModuleInterop": true,                             /* Emit additional JavaScript to ease support for importing CommonJS modules. This enables 'allowSyntheticDefaultImports' for type compatibility. */
    "forceConsistentCasingInFileNames": true,            /* Ensure that casing is correct in imports. */

    /* Type Checking */
    "strict": true,                                      /* Enable all strict type-checking options. */

    /* Completeness */
    "skipLibCheck": true                                 /* Skip type checking all .d.ts files. */
  },
  "include": ["src/**/*"], // 只编译 src 目录下的文件
  "exclude": ["node_modules", "dist"] // 排除这些目录
}
```

### packages/web-client/tsconfig.node.json
```
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}

```

### packages/web-client/index.html
```
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React + TS</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

```

### packages/web-client/tsconfig.app.json
```
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}

```

### packages/web-client/README.md
```
# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

```

### packages/web-client/package.json
```

{
  "name": "@hevno/web-client",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "reactflow": "^11.11.3",
    "zustand": "^4.5.2",
    "axios": "^1.7.2",
    "socket.io-client": "^4.7.5",
    "@hevno/schemas": "workspace:*"
  },
  "devDependencies": {
    "@types/react": "^18.2.66",
    "@types/react-dom": "^18.2.22",
    "@typescript-eslint/eslint-plugin": "^7.2.0",
    "@typescript-eslint/parser": "^7.2.0",
    "@vitejs/plugin-react": "^4.2.1",
    "eslint": "^8.57.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.6",
    "vite": "^5.2.0"
  }
}
```

### packages/web-client/tsconfig.json
```
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}

```

### packages/web-client/eslint.config.js
```
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { globalIgnores } from 'eslint/config'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])

```

### packages/web-client/vite.config.ts
```
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})

```

### packages/web-client/src/App.css
```
#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.react:hover {
  filter: drop-shadow(0 0 2em #61dafbaa);
}

@keyframes logo-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: no-preference) {
  a:nth-of-type(2) .logo {
    animation: logo-spin infinite 20s linear;
  }
}

.card {
  padding: 2em;
}

.read-the-docs {
  color: #888;
}

```

### packages/web-client/src/index.css
```
:root {
  font-family: system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;

  color-scheme: light dark;
  color: rgba(255, 255, 255, 0.87);
  background-color: #242424;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  font-weight: 500;
  color: #646cff;
  text-decoration: inherit;
}
a:hover {
  color: #535bf2;
}

body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}

h1 {
  font-size: 3.2em;
  line-height: 1.1;
}

button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  font-family: inherit;
  background-color: #1a1a1a;
  cursor: pointer;
  transition: border-color 0.25s;
}
button:hover {
  border-color: #646cff;
}
button:focus,
button:focus-visible {
  outline: 4px auto -webkit-focus-ring-color;
}

@media (prefers-color-scheme: light) {
  :root {
    color: #213547;
    background-color: #ffffff;
  }
  a:hover {
    color: #747bff;
  }
  button {
    background-color: #f9f9f9;
  }
}

```

### packages/web-client/src/vite-env.d.ts
```
/// <reference types="vite/client" />

```

### packages/schemas/dist/index.js
```
// packages/schemas/src/index.ts
import { z } from 'zod';
// 在这里放入您设计的 GraphSchema, NodeSchema 等
export const PingRequestSchema = z.object({
    message: z.string(),
});

```

### packages/schemas/dist/index.d.ts
```
import { z } from 'zod';
export declare const PingRequestSchema: z.ZodObject<{
    message: z.ZodString;
}, "strip", z.ZodTypeAny, {
    message: string;
}, {
    message: string;
}>;
export type PingRequest = z.infer<typeof PingRequestSchema>;

```

### packages/schemas/src/index.ts
```
// packages/schemas/src/index.ts
import { z } from 'zod';

// 在这里放入您设计的 GraphSchema, NodeSchema 等
export const PingRequestSchema = z.object({
  message: z.string(),
});
export type PingRequest = z.infer<typeof PingRequestSchema>;


```

### packages/core-engine/src/GraphExecutor.ts
```
import { Graph, GraphNode } from '@hevno/schemas';
import { topologicalSort } from './graph';
import { ExecutionContext, INodeRunner } from './types';
import { FunctionRunner } from './runners/FunctionRunner';

export class GraphExecutor {
  private nodeRunners: Map<string, INodeRunner>;

  constructor() {
    this.nodeRunners = new Map();
    // 注册已有的执行器
    this.nodeRunners.set('function', new FunctionRunner());
    // 未来会添加: this.nodeRunners.set('llm', new LlmRunner());
  }

  public async execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext> {
    const sortedNodeIds = topologicalSort(graph.nodes, graph.edges);
    const context: ExecutionContext = { outputs: {} };

    // 初始化输入节点
    const inputNodes = graph.nodes.filter(n => n.type === 'input');
    for (const inputNode of inputNodes) {
        if (initialInputs[inputNode.id]) {
            context.outputs[inputNode.id] = initialInputs[inputNode.id];
        }
    }

    for (const nodeId of sortedNodeIds) {
      const node = graph.nodes.find(n => n.id === nodeId);
      if (!node || node.type === 'input') continue; // 跳过输入节点

      // 1. 收集当前节点的输入
      const nodeInputs: Record<string, any> = {};
      const incomingEdges = graph.edges.filter(e => e.targetNodeId === nodeId);
      for (const edge of incomingEdges) {
        const sourceOutput = context.outputs[edge.sourceNodeId]?.[edge.sourceOutputId];
        nodeInputs[edge.targetInputId] = sourceOutput;
      }
      
      console.log(`Executing node ${node.name} (${node.id}) with inputs:`, nodeInputs);

      // 2. 找到并运行对应的执行器
      if (node.type === 'processor') {
        const runner = this.nodeRunners.get(node.runtime.type);
        if (runner) {
          const result = await runner.run(node, nodeInputs);
          context.outputs[node.id] = result;
          console.log(`Node ${node.id} produced output:`, result);
        } else {
            console.warn(`No runner found for processor type: ${node.runtime.type}`);
        }
      } else if (node.type === 'output') {
          // 输出节点通常只传递数据
          context.outputs[node.id] = nodeInputs;
      }

      // 可以在这里通过事件发射器或回调来通知外部执行进度
    }

    return context;
  }
}
```

### packages/core-engine/src/types.ts
```
import { GraphNode } from '@hevno/schemas';

// 执行上下文，包含所有节点的输出状态
export type ExecutionContext = {
  // {[nodeId]: {[outputId]: value}}
  outputs: Record<string, Record<string, any>>;
};

// 节点执行器的接口
export interface INodeRunner {
  // 接受节点定义和当前所有上游节点的输入值
  run(node: GraphNode, inputs: Record<string, any>): Promise<Record<string, any>>;
}
```

### packages/core-engine/src/graph.ts
```
import { GraphSchema, GraphNode, Edge } from '@hevno/schemas';

// 使用 Kahn 算法进行拓扑排序
export function topologicalSort(nodes: GraphNode[], edges: Edge[]): string[] {
  const inDegree = new Map<string, number>();
  const adjList = new Map<string, string[]>();
  const sortedOrder: string[] = [];
  const queue: string[] = [];

  // 初始化入度和邻接表
  for (const node of nodes) {
    inDegree.set(node.id, 0);
    adjList.set(node.id, []);
  }

  // 计算每个节点的入度
  for (const edge of edges) {
    adjList.get(edge.sourceNodeId)?.push(edge.targetNodeId);
    inDegree.set(edge.targetNodeId, (inDegree.get(edge.targetNodeId) ?? 0) + 1);
  }

  // 将所有入度为 0 的节点加入队列
  for (const [nodeId, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  // 处理队列中的节点
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    sortedOrder.push(nodeId);

    for (const neighborId of adjList.get(nodeId) ?? []) {
      const newDegree = (inDegree.get(neighborId) ?? 1) - 1;
      inDegree.set(neighborId, newDegree);
      if (newDegree === 0) {
        queue.push(neighborId);
      }
    }
  }

  // 检查是否有环 (如果排序后的节点数不等于总节点数)
  if (sortedOrder.length !== nodes.length) {
    throw new Error('Graph has at least one cycle. Topological sort is not possible.');
  }

  return sortedOrder;
}
```

### packages/core-engine/src/FunctionRunner.ts
```
import { ProcessorNode } from '@hevno/schemas';
import { INodeRunner } from '../types';

// 函数注册表，未来插件可以向这里注册函数
const functionRegistry = new Map<string, (inputs: any) => any>();

// 示例函数
functionRegistry.set('add', (inputs) => ({ result: inputs.a + inputs.b }));
functionRegistry.set('concatenate', (inputs) => ({ result: `${inputs.str1}${inputs.str2}` }));

export class FunctionRunner implements INodeRunner {
  async run(node: ProcessorNode, inputs: Record<string, any>): Promise<Record<string, any>> {
    if (node.runtime.type !== 'function') {
      throw new Error('Invalid node type for FunctionRunner');
    }

    const func = functionRegistry.get(node.runtime.functionName);
    if (!func) {
      throw new Error(`Function "${node.runtime.functionName}" not found in registry.`);
    }

    // 执行函数并返回结果
    // 函数的返回值应该是一个对象，key 是输出端口的 ID
    const result = await Promise.resolve(func(inputs));
    return result;
  }
}
```

### packages/core-engine/src/index.ts
```
export * from './graph';
```

### packages/api-server/src/index.ts
```
// packages/api-server/src/index.ts
import Fastify from 'fastify';
import cors from '@fastify/cors';
import { Server } from 'socket.io';
import { GraphExecutor } from '@hevno/core-engine'; // 导入执行器
import { Graph } from '@hevno/schemas'; // 导入图类型

const fastify = Fastify({ logger: true });

// 注册 CORS
fastify.register(cors, {
  origin: '*', // 开发时允许所有来源
});

// HTTP 路由
fastify.get('/', async (request, reply) => {
  return { message: 'Welcome to Hevno API' };
});

// 启动服务器
const start = async () => {
  try {
    await fastify.listen({ port: 3001 });

    const io = new Server(fastify.server, { cors: { origin: '*' } });
    const graphExecutor = new GraphExecutor(); // 实例化执行器

    io.on('connection', (socket) => {
      fastify.log.info(`Client connected: ${socket.id}`);

      // 监听 'execute_graph' 事件
      socket.on('execute_graph', async (data: { graph: Graph, inputs: Record<string, any> }) => {
        fastify.log.info(`Received execute_graph request from ${socket.id}`);
        try {
          // 这里可以添加 Zod 验证 data.graph 和 data.inputs
          const resultContext = await graphExecutor.execute(data.graph, data.inputs);
          
          // 将最终输出节点的输出发送回客户端
          const outputNodes = data.graph.nodes.filter(n => n.type === 'output');
          const finalOutputs: Record<string, any> = {};
          for (const node of outputNodes) {
              finalOutputs[node.id] = resultContext.outputs[node.id];
          }

          socket.emit('execution_result', { success: true, outputs: finalOutputs });
        } catch (error: any) {
          fastify.log.error(error);
          socket.emit('execution_result', { success: false, error: error.message });
        }
      });

      socket.on('disconnect', () => {
        fastify.log.info(`Client disconnected: ${socket.id}`);
      });
      
      socket.emit('welcome', 'Connected to Hevno WebSocket!');
    });

  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
```
