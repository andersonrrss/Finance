document.addEventListener("DOMContentLoaded", function () {
  tbody = document.querySelector("tbody");

  fetch("/getHistory")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ERROR[${response.status}]`);
      }
      return response.json();
    })
    .then((data) => {
      //Oculta o loader
      document.getElementById("loader").style.display = "none";
      // Checa se algum dado foi recebido
      if (data.length !== 0) {
        // Mostra a tabela
        let table = document.querySelector("table");
        table.style.display = "table";

        let html = "";

        // Itera sobre o array de dados revertido, para que eles fiquem em ordem cronológica
        for (row of data.reverse()) {
          let date = new Date(row.date);
          let day = date.toLocaleDateString(); // Armazena a data da ação DD/MM/AAAA
          let hour = date.toLocaleTimeString(); // Armazena a hora da ação

          html += `
                <tr>
                    <th scope="row">${row.action}</th>
                    <td>${row.symbol}</td>
                    <td>${row.price}</td>
                    <td>${row.shares}</td>
                    <td>${hour}</td>
                    <td>${day}</td>
                </tr>
            `;
        }
        // Atualiza os dados do html
        tbody.innerHTML = html;
        return;
      }

      // Mostra a mensagem se a requisição não recebeu nenhum dado
      document.getElementById("mensagem").style.display = "block";
    })
    .catch((err) => {
      console.error(`ERRO[${err}]`);
    });
});
