import fs from 'fs';
import fetch from 'node-fetch';
import cheerio from 'cheerio';

const CONTENT_URL = 'https://petbridge.org/animals/animals-all-responsive.php?ClientID=17&Species=Dog';

async function fetchHTML(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const html = await response.text();
        const $ = cheerio.load(html);
        const animals = [];

        $('.animal_list_box_dog').each((index, element) => {
            const href = $(element).find('a').attr('href');
            const photoUrl = $(element).find('.results_animal_photo img').attr('src');
            const name = $(element).find('.results_animal_name').text().trim();
            const sex = $(element).find('.results_animal_detail_data_Sex').text().trim();
            const breed = $(element).find('.results_animal_detail_data_PrimaryBreed').text().trim();
            const age = $(element).find('.results_animal_detail_data_Age').text().trim();

            animals.push({
                href,
                photoUrl,
                name,
                sex,
                breed,
                age
            });
        });

        fs.writeFileSync('./output/animals.json', JSON.stringify(animals, null, 2), 'utf8');
        console.log('Animal data saved to ./output/animals.json');
    } catch (error) {
        console.error('Error fetching HTML:', error);
    }
}

fetchHTML(CONTENT_URL);
