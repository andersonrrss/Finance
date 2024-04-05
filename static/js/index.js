document.addEventListener("DOMContentLoaded", function () {
  const tbody = document.querySelector("tbody");

  fetch("/stock")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ERROR ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      let html = "";
      if (data.buys.length !== 0) {
        // Armazena a primeira linha e coloca as informações adicionais
        let firstQuote = data.buys.shift();
        html += `
        <tr>
            <th scope="row">${firstQuote.name}</th>
            <td>${firstQuote.symbol}</td>
            <td>${firstQuote.price}</td>
            <td>${firstQuote.shares}</td>
            <td>${firstQuote.totalPrice}</td>
            <td>${data.totalQuotes}</td>
            <td>${data.cash}
            <td>${data.total}</td>
        </tr>
        `;
        // Itera sobre o resto dos dados e os mostra para o usuário
        data["buys"].forEach((quote) => {
          html += `
            <tr>
                <th scope="row">${quote.name}</th>
                <td>${quote.symbol}</td>
                <td>${quote.price}</td>
                <td>${quote.shares}</td>
                <td>${quote.totalPrice}</td>
            </tr>
            `;
        });
        tbody.innerHTML = html;
        return;
      }

      // Se o usuário não tiver nenhuma ação comprada
      html = `
        <tr>
            <td scope="row"></td>
            <td></td>
            <td></td>
            <td></td>
            <td>0</td>
            <td>${data.cash}
            <td>${data.total}</td>
        </tr>
      `
      tbody.innerHTML = html;
    })
    .catch((err) => {
      console.error(`ERRO[${err}]`);
    });
});
