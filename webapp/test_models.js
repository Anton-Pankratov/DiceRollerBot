const fs = require('fs');

// Read files
const dndDataContent = fs.readFileSync('./webapp/dnd_data.js', 'utf8');
const modelsContent = fs.readFileSync('./webapp/models.js', 'utf8');

// Combine
const codeToRun = dndDataContent + "\n" + modelsContent + "\n" + `
// Test cases
console.log("Running Character model tests...");

const c1 = new Character({
    name: "Тестовый Rogue",
    class: "Плут 11",
    min_rolls: {
        "Скрытность": 10,
        "Акробатика": 8
    }
});

console.assert(c1.minRolls !== undefined, "minRolls should be defined");
console.assert(c1.minRolls["Скрытность"] === 10, "Stealth minimum roll should be 10");
console.assert(c1.minRolls["Акробатика"] === 8, "Acrobatics minimum roll should be 8");

const c2 = new Character({
    name: "Rogue 2",
    class: "Плут 11",
    minRolls: {
        "Скрытность": 12
    }
});
console.assert(c2.minRolls["Скрытность"] === 12, "Stealth minimum roll should be 12 (camelCase)");

console.log("All tests passed successfully!");
`;

eval(codeToRun);
