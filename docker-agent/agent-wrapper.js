#!/usr/bin/env node
/**
 * ClawSwarm Agent Wrapper
 * 
 * Runs inside Docker container, handles:
 * - Health check endpoint
 * - Task receiving
 * - OpenClaw execution
 * - Result reporting to orchestrator
 */

const http = require('http');
const { spawn, execSync } = require('child_process');
const https = require('https');

const AGENT_ID = process.env.AGENT_ID || 'unknown';
const AGENT_NAME = process.env.AGENT_NAME || 'unnamed';
const AGENT_TYPE = process.env.AGENT_TYPE || 'custom';
const AGENT_TASK = process.env.AGENT_TASK || '';
const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://host.docker.internal:8420';

let currentTask = null;
let taskResult = null;
let isRunning = false;
let status = 'idle';

console.log(`🦞 Agent ${AGENT_NAME} (${AGENT_ID}) starting...`);
console.log(`   Type: ${AGENT_TYPE}`);
console.log(`   Orchestrator: ${ORCHESTRATOR_URL}`);

// Execute a task using OpenClaw
async function executeTask(task) {
    console.log(`📋 Executing task: ${task.substring(0, 100)}...`);
    isRunning = true;
    status = 'busy';
    currentTask = task;
    
    return new Promise((resolve, reject) => {
        // Use openclaw agent --local to execute the task embedded
        // --local runs the agent locally using API keys from env
        // --session-id identifies this agent's session
        // Model is configured via openclaw.json (agents.defaults.model.primary)
        const proc = spawn('openclaw', ['agent', '--local', '--session-id', AGENT_ID, '--message', task], {
            cwd: '/workspace',
            env: {
                ...process.env,
                HOME: '/workspace',
                OPENCLAW_WORKSPACE: '/workspace',
            },
            stdio: ['pipe', 'pipe', 'pipe'],
        });
        
        let output = '';
        let errorOutput = '';
        
        proc.stdout.on('data', (data) => {
            output += data.toString();
            console.log(`[stdout] ${data.toString().trim()}`);
        });
        
        proc.stderr.on('data', (data) => {
            errorOutput += data.toString();
            console.log(`[stderr] ${data.toString().trim()}`);
        });
        
        proc.on('close', (code) => {
            isRunning = false;
            status = 'idle';
            
            if (code === 0) {
                taskResult = output;
                resolve(output);
            } else {
                taskResult = `Error (code ${code}): ${errorOutput}`;
                reject(new Error(taskResult));
            }
            
            // Report result to orchestrator
            reportResult(task, taskResult, code === 0 ? 'success' : 'error');
        });
        
        // Timeout after 30 minutes
        setTimeout(() => {
            if (isRunning) {
                proc.kill();
                reject(new Error('Task timeout'));
            }
        }, 30 * 60 * 1000);
    });
}

// Report result back to orchestrator
function reportResult(task, result, status) {
    const data = JSON.stringify({
        agent_id: AGENT_ID,
        task: task,
        result: result,
        status: status,
    });
    
    const url = new URL(`${ORCHESTRATOR_URL}/agents/${AGENT_ID}/result`);
    const options = {
        hostname: url.hostname,
        port: url.port || 80,
        path: url.pathname,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(data),
        },
    };
    
    const req = http.request(options, (res) => {
        console.log(`📤 Reported result to orchestrator: ${res.statusCode}`);
    });
    
    req.on('error', (e) => {
        console.error(`❌ Failed to report result: ${e.message}`);
    });
    
    req.write(data);
    req.end();
}

// HTTP server for health checks and task receiving
const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    
    // Health check
    if (url.pathname === '/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            status: 'healthy',
            agent_id: AGENT_ID,
            agent_name: AGENT_NAME,
            agent_type: AGENT_TYPE,
            agent_status: status,
            is_running: isRunning,
        }));
        return;
    }
    
    // Get status
    if (url.pathname === '/status' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            agent_id: AGENT_ID,
            agent_name: AGENT_NAME,
            agent_type: AGENT_TYPE,
            status: status,
            is_running: isRunning,
            current_task: currentTask,
            last_result: taskResult,
        }));
        return;
    }
    
    // Assign task
    if (url.pathname === '/task' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { task } = JSON.parse(body);
                
                if (isRunning) {
                    res.writeHead(409, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Agent is busy' }));
                    return;
                }
                
                res.writeHead(202, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'accepted', task }));
                
                // Execute task asynchronously
                executeTask(task).catch(console.error);
            } catch (e) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: e.message }));
            }
        });
        return;
    }
    
    // Get result
    if (url.pathname === '/result' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            agent_id: AGENT_ID,
            task: currentTask,
            result: taskResult,
            status: isRunning ? 'running' : (taskResult ? 'complete' : 'idle'),
        }));
        return;
    }
    
    // 404
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
});

const PORT = 8421;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`🌐 Agent API listening on port ${PORT}`);
    
    // If initial task provided, execute it
    if (AGENT_TASK) {
        console.log(`📋 Initial task provided, executing...`);
        executeTask(AGENT_TASK).catch(console.error);
    }
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('Received SIGTERM, shutting down...');
    server.close();
    process.exit(0);
});
