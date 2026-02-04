# MoltMud Server Migration Guide

This document describes the process for migrating MoltMud from a shared server to a dedicated server instance.

## Prerequisites

- Root/sudo access to both old and new servers
- SSH key pair for migration user
- DNS control for `mud.example.com` (or your domain)

## Migration Steps

### 1. Provision New Server

Run setup script on new server:
