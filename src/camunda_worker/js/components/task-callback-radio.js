const CLASS_SELECTED = 'task-callback-radio__doc--selected';

const bindEvents = (taskCallbackNode) => {
    const radioSelects = taskCallbackNode.querySelectorAll('input');
    const descriptions = taskCallbackNode.querySelector('.task-callback-radio__description');

    radioSelects.forEach(radioSelect => {
        radioSelect.addEventListener('change', (event) => {
            const id = event.target.id;

            // hide all descriptions
            descriptions
                .querySelectorAll(`.${CLASS_SELECTED}`)
                .forEach(node => {
                    node.classList.remove(CLASS_SELECTED);
                });

            // show the matching doc
            document.getElementById(`${id}-doc`)
                .classList
                .add(CLASS_SELECTED);
        });
    });
};


const init = () => {
    const nodes = document.querySelectorAll('.task-callback-radio');
    nodes.forEach(bindEvents);
};


init();
