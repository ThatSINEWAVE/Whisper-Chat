// Function to update the dashboard
function updateDashboard() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // Update client count
            document.getElementById('client-count').textContent = data.client_count;

            // Update clients list
            const clientsList = document.getElementById('clients-list');
            clientsList.innerHTML = '';

            data.clients.forEach(client => {
                const row = document.createElement('tr');
                const cell = document.createElement('td');
                cell.textContent = client;
                row.appendChild(cell);
                clientsList.appendChild(row);
            });

            // Update logs
            const logsList = document.getElementById('logs-list');
            logsList.innerHTML = '';

            data.logs.forEach(log => {
                const row = document.createElement('tr');

                const timestampCell = document.createElement('td');
                timestampCell.textContent = log.timestamp;
                row.appendChild(timestampCell);

                const typeCell = document.createElement('td');
                typeCell.textContent = log.type;
                typeCell.className = log.type.toLowerCase();
                row.appendChild(typeCell);

                const messageCell = document.createElement('td');
                messageCell.textContent = log.message;
                row.appendChild(messageCell);

                logsList.appendChild(row);
            });

            // Scroll to bottom of logs
            const logsContainer = document.querySelector('.logs');
            logsContainer.scrollTop = logsContainer.scrollHeight;
        });
}

// Update dashboard initially and every 2 seconds
updateDashboard();
setInterval(updateDashboard, 2000);