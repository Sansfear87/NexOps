# Frontend Package: AI DevOps Assistant
 
**Framework:** React 18 with TypeScript and Vite  
**Status:** Phase 13 Complete (Developer Console UI)

## Overview
This directory contains the Single-Page Application (SPA) developer console for the AI DevOps Assistant.
It features a full tabbed control plane for:
- User authentication & session management (Register, Login, JWT tokens)
- Project creation, selection, and deletion
- Team membership & RBAC permission controls (`OWNER`, `MAINTAINER`, `DEVELOPER`, `VIEWER`)
- Project-scoped API Key lifecycle management (create with scopes, revoke)
- GitHub repository connection & status monitoring
- Pull Request feed with manual and automated "⚡ Run AI Review" triggers
- Live platform event stream (EventBus canonical events: `PR_OPENED`, `REVIEW_STARTED`, etc.)
- Health probe indicators

## Commands
```bash
# Install dependencies
npm install

# Run local development server
npm run dev

# Typecheck and build production bundle
npm run build
```
